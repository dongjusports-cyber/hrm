"""Lớp A — nhắc việc rule-based (0 token Gemini). P2.5: Agent sync lỗi → Admin."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.ai.models import AiAlert
from app.modules.ai.vi_labels import label_period_status, label_sync_status
from app.modules.ai.schemas import AiAlertCreate, AiAlertOut, AiAlertsMineOut
from app.modules.core.models import User
from app.modules.integration.models import SyncJob


def _to_out(row: AiAlert) -> AiAlertOut:
    return AiAlertOut.model_validate(row)


def create_alert(db: Session, body: AiAlertCreate) -> AiAlertOut | None:
    """Tạo alert; trùng source_ref → bỏ qua (idempotent)."""
    if body.source_ref:
        existing = db.query(AiAlert).filter(AiAlert.source_ref == body.source_ref).one_or_none()
        if existing:
            return _to_out(existing)

    row = AiAlert(
        rule_key=body.rule_key.strip(),
        title=body.title.strip(),
        body=(body.body or "").strip(),
        target_module=body.target_module.strip() or "timekeeping",
        user_id=body.user_id,
        source_ref=body.source_ref,
        is_read=False,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if body.source_ref:
            existing = db.query(AiAlert).filter(AiAlert.source_ref == body.source_ref).one_or_none()
            if existing:
                return _to_out(existing)
        raise
    db.refresh(row)
    return _to_out(row)


def emit_sync_job_alert(db: Session, job: SyncJob) -> AiAlertOut | None:
    """
    Rule: Agent sync lỗi / partial → nhắc Admin (05§5.3).
    - error → sync_error
    - partial → sync_partial (MSNV lạ, dữ liệu thiếu…)
    """
    if job.status not in ("error", "partial"):
        return None

    if job.status == "error":
        rule_key = "sync_error"
        title = "Trợ Lý AI: Agent đồng bộ Mitapro bị lỗi"
    else:
        rule_key = "sync_partial"
        title = "Trợ Lý AI: Đồng bộ Mitapro chưa đầy đủ"

    body = (
        f"Trạng thái: {label_sync_status(job.status)}. "
        f"Đã nhập {job.records_inserted}, bỏ trùng {job.records_skipped}, nhận {job.records_in}. "
        f"{job.message}"
    ).strip()

    return create_alert(
        db,
        AiAlertCreate(
            rule_key=rule_key,
            title=title,
            body=body,
            target_module="timekeeping",
            user_id=None,  # broadcast Admin
            source_ref=f"sync_job:{job.id}",
        ),
    )


def evaluate_sync_streak(db: Session, *, streak: int = 3) -> AiAlertOut | None:
    """Nếu N job agent gần nhất đều error → nhắc thêm (rule phụ)."""
    recent = (
        db.query(SyncJob)
        .filter(SyncJob.source == "mitapro", SyncJob.status.in_(["success", "partial", "error"]))
        .order_by(SyncJob.started_at.desc())
        .limit(streak)
        .all()
    )
    if len(recent) < streak:
        return None
    if not all(j.status == "error" for j in recent):
        return None
    newest = recent[0]
    return create_alert(
        db,
        AiAlertCreate(
            rule_key="sync_error_streak",
            title=f"Trợ Lý AI: Agent lỗi {streak} lần liên tiếp",
            body=(
                f"Đề xuất kiểm tra Agent trên máy Mitapro (ODBC, dịch vụ, token). "
                f"Lỗi gần nhất: {newest.message}"
            ),
            target_module="timekeeping",
            user_id=None,
            source_ref=f"sync_streak:{newest.id}",
        ),
    )


def _visible_to(user: User, alert: AiAlert) -> bool:
    if alert.user_id is not None:
        return alert.user_id == user.id
    # Broadcast: sync_* → Admin; dispute_new → dispute|payroll (05§5.3)
    if alert.rule_key.startswith("sync_"):
        return user.role == "admin"
    if alert.rule_key in (
        "dispute_new",
        "dispute_stale",
        "payslip_unconfirmed",
        "period_lock_overdue",
    ):
        if user.role == "admin":
            return True
        return user.has_module("dispute") or user.has_module("payroll")
    if alert.rule_key == "wt_regime_expiring":
        if user.role == "admin":
            return True
        return user.has_module("hr")
    if alert.rule_key == "punch_odd":
        if user.role == "admin":
            return True
        return user.has_module("timekeeping") or user.has_module("hr")
    if alert.rule_key.startswith("kpi_"):
        if user.role == "admin":
            return True
        return user.has_module("report") or user.has_module("overview")
    if user.role == "admin":
        return True
    return user.has_module(alert.target_module)


def evaluate_payroll_reminders(db: Session) -> None:
    """
    05§5.3 — lazy khi mở badge:
    - Phiếu published quá hạn xác nhận
    - Kỳ lương chưa khóa sau ngày trả lương (08 tháng sau)
    """
    from app.modules.attendance.models import PayPeriod
    from app.modules.payroll.models import Payslip

    from app.modules.attendance.engine import VN_TZ

    today = datetime.now(tz=VN_TZ).date()

    overdue_slips = (
        db.query(Payslip)
        .filter(
            Payslip.status == "published",
            Payslip.confirm_deadline.isnot(None),
            Payslip.confirm_deadline < today,
        )
        .limit(200)
        .all()
    )
    if overdue_slips:
        # Gom theo kỳ
        by_period: dict[str, int] = {}
        for s in overdue_slips:
            pay = db.get(PayPeriod, s.pay_period_id)
            if pay is None:
                continue
            key = f"{pay.year:04d}-{pay.month:02d}"
            by_period[key] = by_period.get(key, 0) + 1
        for period, n in by_period.items():
            create_alert(
                db,
                AiAlertCreate(
                    rule_key="payslip_unconfirmed",
                    title=f"Trợ Lý AI: {n} phiếu kỳ {period} quá hạn xác nhận",
                    body=(
                        f"Có {n} phiếu đã phát hành nhưng công nhân chưa xác nhận "
                        f"sau hạn. Vào Tính Lương / Khiếu Nại để theo dõi."
                    ),
                    target_module="payroll",
                    user_id=None,
                    source_ref=f"payslip_unconfirmed:{period}:{today.isoformat()}",
                ),
            )

    # Kỳ chưa khóa sau ngày trả lương 08 tháng sau (10.3#1)
    periods = (
        db.query(PayPeriod)
        .filter(PayPeriod.status.in_(["open", "calculating", "published"]))
        .all()
    )
    for pay in periods:
        # Ngày trả lương = 08 tháng kế tiếp
        if pay.month == 12:
            pay_year, pay_month = pay.year + 1, 1
        else:
            pay_year, pay_month = pay.year, pay.month + 1
        payday = date(pay_year, pay_month, 8)
        if today <= payday:
            continue
        period = f"{pay.year:04d}-{pay.month:02d}"
        create_alert(
            db,
            AiAlertCreate(
                rule_key="period_lock_overdue",
                title=f"Trợ Lý AI: kỳ {period} chưa khóa (đã qua ngày trả lương)",
                body=(
                    f"Ngày trả lương mục tiêu {payday.isoformat()} đã qua mà kỳ còn "
                    f"«{label_period_status(pay.status)}». Đề xuất hoàn tất phát hành và khóa kỳ."
                ),
                target_module="payroll",
                user_id=None,
                source_ref=f"period_lock_overdue:{period}",
            ),
        )


_WT_REGIME_LABEL = {
    "PREGNANT": "Đang mang thai",
    "MATERNITY": "Nghỉ thai sản",
    "CHILD": "Nuôi con nhỏ",
}


def evaluate_wt_regime_reminders(db: Session) -> None:
    """22§22.14 / Bước F — nhắc HR khi chế độ về sớm còn 3 ngày (date_to = today+3)."""
    from app.modules.mdm.models import Employee, EmployeeWtRegime

    from app.modules.attendance.engine import VN_TZ

    today = datetime.now(tz=VN_TZ).date()
    target = today + timedelta(days=3)
    rows = (
        db.query(EmployeeWtRegime, Employee)
        .join(Employee, Employee.id == EmployeeWtRegime.employee_id)
        .filter(
            EmployeeWtRegime.date_to == target,
            EmployeeWtRegime.date_from <= today,
            EmployeeWtRegime.ended_at.is_(None),
            Employee.deleted_at.is_(None),
        )
        .all()
    )
    for regime, emp in rows:
        label = _WT_REGIME_LABEL.get(regime.regime_type, regime.regime_type)
        date_to_str = regime.date_to.strftime("%d/%m/%Y")
        hours_bit = "" if regime.regime_type == "MATERNITY" else f" ({regime.hours_early}h)"
        create_alert(
            db,
            AiAlertCreate(
                rule_key="wt_regime_expiring",
                title=f"Trợ Lý AI: chế độ {label} MSNV {emp.employee_code} sắp hết hạn",
                body=(
                    f"MSNV {emp.employee_code} — {label}{hours_bit}, "
                    f"hết {date_to_str} (còn 3 ngày). Gia hạn hoặc chấm dứt trên hồ sơ."
                ),
                target_module="hr",
                user_id=None,
                source_ref=f"wt_regime:{regime.id}:{regime.date_to.isoformat()}",
            ),
        )


def evaluate_punch_reminders(db: Session) -> None:
    """Luật 01 — thiếu vào hoặc ra: AI cảnh báo HR, không bịa giờ."""
    from app.modules.attendance.engine import VN_TZ
    from app.modules.attendance.review import count_odd_punches, list_odd_punches

    today = datetime.now(tz=VN_TZ).date()
    date_from = today.replace(day=1)
    n = count_odd_punches(db, date_from, today)
    if n <= 0:
        return
    rows = list_odd_punches(db, date_from, today, limit=8)
    sample = ", ".join(
        f"{emp.employee_code} {day.work_date.strftime('%d/%m')}" for day, emp in rows
    )
    more = "" if n <= 8 else f" … (+{n - 8})"
    period = f"{today.year:04d}-{today.month:02d}"
    create_alert(
        db,
        AiAlertCreate(
            rule_key="punch_odd",
            title=f"Trợ Lý AI: {n} dòng chấm lẻ kỳ {period} (thiếu vào hoặc ra)",
            body=(
                f"Có {n} ngày công chỉ có một mốc — không tự bịa giờ, chưa tính công/trễ/sớm. "
                f"HR gọi NV lập biên bản rồi chấm tay đủ cặp. "
                f"Ví dụ: {sample}{more}."
            ),
            target_module="timekeeping",
            user_id=None,
            source_ref=f"punch_odd:{period}:{today.isoformat()}",
        ),
    )


def evaluate_kpi_threshold_alerts(db: Session, *, period: str | None = None) -> None:
    """04§4.6 / 02§2.4 — cảnh báo khi KPI kỳ vượt ngưỡng policy."""
    from app.modules.attendance.models import PayPeriod
    from app.modules.payroll.money import D
    from app.modules.policy.models import PolicyPackage
    from app.modules.policy.seed_payload import default_payload
    from app.modules.report.service import compute_kpi

    if period:
        y_s, m_s = period.split("-", 1)
        y, m = int(y_s), int(m_s)
    else:
        from app.modules.attendance.engine import VN_TZ

        today = datetime.now(tz=VN_TZ).date()
        y, m = today.year, today.month
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        period = f"{y:04d}-{m:02d}"

    pay = (
        db.query(PayPeriod)
        .filter(PayPeriod.year == y, PayPeriod.month == m)
        .one_or_none()
    )
    if pay is None:
        return

    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    payload = dict(pkg.payload) if pkg and isinstance(pkg.payload, dict) else default_payload()
    for k, v in default_payload().items():
        payload.setdefault(k, v)

    kpi = compute_kpi(db, period)
    att_min = D(payload.get("kpi_attendance_min_pct") or 0)
    ot_max = D(payload.get("kpi_ot_rate_max_pct") or 100)
    turn_max = D(payload.get("kpi_turnover_max_pct") or 100)
    dept_ot_max = D(payload.get("kpi_ot_dept_max_pct") or 100)

    if kpi.attendance_rate_pct is not None and D(kpi.attendance_rate_pct) < att_min:
        create_alert(
            db,
            AiAlertCreate(
                rule_key="kpi_attendance_low",
                title=f"Trợ Lý AI: chuyên cần kỳ {period} dưới ngưỡng",
                body=(
                    f"Chuyên cần {kpi.attendance_rate_pct}% < ngưỡng {att_min}% "
                    f"(chính sách kpi_attendance_min_pct). Kiểm tra Báo cáo KPI."
                ),
                target_module="report",
                user_id=None,
                source_ref=f"kpi_attendance_low:{period}",
            ),
        )

    if kpi.ot_rate_pct is not None and D(kpi.ot_rate_pct) > ot_max:
        create_alert(
            db,
            AiAlertCreate(
                rule_key="kpi_ot_high",
                title=f"Trợ Lý AI: tỷ lệ OT kỳ {period} vượt ngưỡng",
                body=(
                    f"Tỷ lệ OT {kpi.ot_rate_pct}% > ngưỡng {ot_max}% "
                    f"(chính sách kpi_ot_rate_max_pct)."
                ),
                target_module="report",
                user_id=None,
                source_ref=f"kpi_ot_high:{period}",
            ),
        )

    if kpi.turnover_rate_pct is not None and D(kpi.turnover_rate_pct) > turn_max:
        create_alert(
            db,
            AiAlertCreate(
                rule_key="kpi_turnover_high",
                title=f"Trợ Lý AI: tỷ lệ nghỉ việc kỳ {period} vượt ngưỡng",
                body=(
                    f"Tỷ lệ nghỉ việc {kpi.turnover_rate_pct}% > ngưỡng {turn_max}% "
                    f"(chính sách kpi_turnover_max_pct)."
                ),
                target_module="report",
                user_id=None,
                source_ref=f"kpi_turnover_high:{period}",
            ),
        )

    offenders: list[str] = []
    for row in kpi.by_department:
        if row.headcount <= 0:
            continue
        ref = D(row.headcount) * D(kpi.official_work_days or 0) * D(kpi.hours_per_day or 8)
        if ref <= 0:
            continue
        rate_pct = (D(row.ot_hours) / ref) * D(100)
        if rate_pct > dept_ot_max:
            offenders.append(
                f"{row.department_code} ({rate_pct.quantize(D('0.01'))}%)"
            )
    if offenders:
        create_alert(
            db,
            AiAlertCreate(
                rule_key="kpi_ot_dept_high",
                title=f"Trợ Lý AI: {len(offenders)} bộ phận OT vượt ngưỡng kỳ {period}",
                body=(
                    f"Ngưỡng bộ phận {dept_ot_max}% (chính sách kpi_ot_dept_max_pct). "
                    f"Vượt: {', '.join(offenders[:8])}"
                    + ("…" if len(offenders) > 8 else "")
                ),
                target_module="report",
                user_id=None,
                source_ref=f"kpi_ot_dept_high:{period}",
            ),
        )


def list_mine(db: Session, user: User, *, unread_only: bool = False, limit: int = 50) -> AiAlertsMineOut:
    # Lazy rule engine (0 token) — 05§5.3
    try:
        evaluate_payroll_reminders(db)
        evaluate_wt_regime_reminders(db)
        evaluate_punch_reminders(db)
        evaluate_kpi_threshold_alerts(db)
    except Exception:  # noqa: BLE001 — không chặn badge nếu rule lỗi
        pass
    q = db.query(AiAlert).order_by(AiAlert.created_at.desc()).limit(200)
    rows = [r for r in q.all() if _visible_to(user, r)]
    if unread_only:
        rows = [r for r in rows if not r.is_read]
    rows = rows[:limit]
    unread = sum(1 for r in rows if not r.is_read)
    # unread_count phải đếm toàn bộ visible unread, không chỉ trong page
    all_visible = [r for r in db.query(AiAlert).order_by(AiAlert.created_at.desc()).limit(500).all() if _visible_to(user, r)]
    unread_total = sum(1 for r in all_visible if not r.is_read)
    return AiAlertsMineOut(unread_count=unread_total, alerts=[_to_out(r) for r in rows])


def mark_read(db: Session, user: User, alert_id: UUID) -> AiAlertOut:
    row = db.get(AiAlert, alert_id)
    if row is None or not _visible_to(user, row):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy nhắc việc này.",
        )
    row.is_read = True
    db.commit()
    db.refresh(row)
    return _to_out(row)


def mark_all_read(db: Session, user: User) -> dict:
    rows = [r for r in db.query(AiAlert).filter(AiAlert.is_read.is_(False)).all() if _visible_to(user, r)]
    for r in rows:
        r.is_read = True
    db.commit()
    return {"ok": True, "marked": len(rows), "message": f"Đã đọc {len(rows)} nhắc việc."}
