"""P3.6 — Phát hành / khóa kỳ lương (payslip_publisher ≠ formula_engine)."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from app.modules.payroll.payslip_out import payslip_out
from app.modules.payroll.schemas import PeriodActionResult, PeriodOut, PayslipOut
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload


def _policy(db: Session) -> dict:
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        return dict(pkg.payload)
    return default_payload()


def period_out(pay: PayPeriod) -> PeriodOut:
    return PeriodOut(
        id=pay.id,
        period=f"{pay.year:04d}-{pay.month:02d}",
        year=pay.year,
        month=pay.month,
        date_from=pay.date_from,
        date_to=pay.date_to,
        official_work_days=pay.official_work_days,
        salary_divisor=pay.salary_divisor,
        status=pay.status,
    )


def get_period(db: Session, period: str) -> PeriodOut:
    return period_out(ensure_pay_period(db, period))


def publish_period(db: Session, period: str, *, actor: User | None = None) -> PeriodActionResult:
    pay = ensure_pay_period(db, period)
    if pay.status == "locked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: kỳ lương đã khóa — không phát hành lại.",
        )
    slips = db.query(Payslip).filter(Payslip.pay_period_id == pay.id).all()
    if not slips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: chưa có phiếu lương — hãy bấm Tính lương trước.",
        )

    days = int((_policy(db).get("payslip_confirm_days") or 7))
    deadline = date.today() + timedelta(days=max(1, days))
    published = 0
    for s in slips:
        if s.status == "draft":
            s.status = "published"
            s.confirm_deadline = deadline
            published += 1
        elif s.status == "resolved":
            # Có thể phát hành lại sau xử lý khiếu nại
            s.status = "published"
            s.confirm_deadline = deadline
            published += 1

    if published == 0 and pay.status == "published":
        return PeriodActionResult(
            period=period_out(pay),
            affected_payslips=0,
            message=f"Kỳ {period} đã phát hành trước đó — không có phiếu draft mới.",
        )

    if published == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: không có phiếu draft để phát hành.",
        )

    pay.status = "published"
    db.commit()
    db.refresh(pay)
    if actor is not None:
        write_audit(
            db,
            actor=actor,
            action="payroll.publish",
            entity_type="pay_period",
            entity_id=period,
            summary=f"Phát hành {published} phiếu kỳ {period}",
            meta={"affected": published, "confirm_deadline": deadline.isoformat()},
        )
    return PeriodActionResult(
        period=period_out(pay),
        affected_payslips=published,
        message=(
            f"Đã phát hành {published} phiếu kỳ {period}. "
            f"Công nhân xem được đến hạn xác nhận {deadline.isoformat()}."
        ),
    )


def lock_period(db: Session, period: str, *, actor: User | None = None) -> PeriodActionResult:
    pay = ensure_pay_period(db, period)
    if pay.status == "locked":
        return PeriodActionResult(
            period=period_out(pay),
            affected_payslips=0,
            message=f"Kỳ {period} đã khóa sẵn.",
        )
    if pay.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: chỉ khóa kỳ sau khi đã Phát hành (published).",
        )
    from app.modules.attendance.review import count_blocking_issues

    punch_issues = count_blocking_issues(db, period)
    count = db.query(Payslip).filter(Payslip.pay_period_id == pay.id).count()
    pay.status = "locked"
    db.commit()
    db.refresh(pay)
    if actor is not None:
        write_audit(
            db,
            actor=actor,
            action="payroll.lock",
            entity_type="pay_period",
            entity_id=period,
            summary=f"Khóa kỳ lương {period} ({count} phiếu)",
            meta={"payslip_count": count, "attendance_punch_issues": punch_issues},
        )
    warn = ""
    if punch_issues > 0:
        warn = (
            f" Cảnh báo R3: còn {punch_issues} ngày thiếu/lẻ punch "
            f"(đã khóa; kiểm tra Chấm Công → Rà soát công)."
        )
    return PeriodActionResult(
        period=period_out(pay),
        affected_payslips=count,
        message=(
            f"Đã khóa kỳ {period}. Không tính lại / phát hành cho đến khi Admin mở khóa."
            + warn
        ),
    )


def unlock_period(db: Session, period: str, *, actor: User) -> PeriodActionResult:
    """Admin mở khóa kỳ (06§6.7 — audit ai mở khóa). locked → published."""
    pay = ensure_pay_period(db, period)
    if pay.status != "locked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: kỳ {period} không ở trạng thái khóa (hiện: {pay.status}).",
        )
    count = db.query(Payslip).filter(Payslip.pay_period_id == pay.id).count()
    pay.status = "published"
    db.commit()
    db.refresh(pay)
    write_audit(
        db,
        actor=actor,
        action="payroll.unlock",
        entity_type="pay_period",
        entity_id=period,
        summary=f"Mở khóa kỳ lương {period} ({count} phiếu) → published",
        meta={"payslip_count": count, "to_status": "published"},
    )
    return PeriodActionResult(
        period=period_out(pay),
        affected_payslips=count,
        message=(
            f"Đã mở khóa kỳ {period} (về trạng thái Phát hành). "
            f"Muốn tính lại: dùng «Mở lại để tính» (Admin)."
        ),
    )


def reopen_period(db: Session, period: str, *, actor: User) -> PeriodActionResult:
    """
    Admin mở lại kỳ để tính lương (published|locked → calculating).
    Phiếu đã confirmed giữ nguyên (P8); phiếu published/disputed/… → draft.
    """
    pay = ensure_pay_period(db, period)
    if pay.status not in ("published", "locked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI: chỉ mở lại kỳ đã phát hành hoặc đã khóa "
                f"(hiện: {pay.status})."
            ),
        )
    slips = db.query(Payslip).filter(Payslip.pay_period_id == pay.id).all()
    reset = 0
    kept_confirmed = 0
    for slip in slips:
        if slip.status == "confirmed":
            kept_confirmed += 1
            continue
        if slip.status != "draft":
            slip.status = "draft"
            slip.confirmed_at = None
            # giữ confirm_deadline cũ hoặc xóa — xóa để publish lại set mới
            slip.confirm_deadline = None
            reset += 1
    from_status = pay.status
    pay.status = "calculating"
    db.commit()
    db.refresh(pay)
    write_audit(
        db,
        actor=actor,
        action="payroll.reopen",
        entity_type="pay_period",
        entity_id=period,
        summary=(
            f"Mở lại kỳ {period} ({from_status}→calculating): "
            f"reset {reset} phiếu, giữ {kept_confirmed} đã xác nhận"
        ),
        meta={
            "from_status": from_status,
            "reset_drafts": reset,
            "kept_confirmed": kept_confirmed,
        },
    )
    return PeriodActionResult(
        period=period_out(pay),
        affected_payslips=reset,
        message=(
            f"Đã mở lại kỳ {period} để tính lương. "
            f"Đưa {reset} phiếu về nháp; giữ {kept_confirmed} phiếu công nhân đã xác nhận. "
            f"Bấm Tính lương → Phát hành lại khi xong."
        ),
    )


def get_payslip(db: Session, payslip_id: UUID) -> PayslipOut:
    row = (
        db.query(Payslip, Employee, TimesheetMonth, PayPeriod)
        .join(Employee, Employee.id == Payslip.employee_id)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .filter(Payslip.id == payslip_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy phiếu lương.",
        )
    slip, emp, ts, pay = row
    return payslip_out(
        slip,
        emp,
        worked_days=ts.worked_days if ts else None,
        al_days=ts.al_days if ts else None,
        rem_days=ts.rem_days if ts else None,
        salary_divisor=pay.salary_divisor,
        period=f"{pay.year:04d}-{pay.month:02d}",
    )
