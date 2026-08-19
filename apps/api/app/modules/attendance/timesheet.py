"""Timesheet tháng — tổng hợp từ attendance_days + điều chỉnh tay."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Collection
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.attendance.models import (
    AttendanceDay,
    LeaveType,
    PayPeriod,
    TimesheetAdjustment,
    TimesheetMonth,
    TimesheetMonthDetail,
)
from app.modules.attendance.schemas import (
    AdjustmentCreate,
    AdjustmentOut,
    LeaveTypeOut,
    PayPeriodOut,
    RebuildTimesheetResult,
    TimesheetMonthDetailOut,
    TimesheetMonthOut,
)
from app.modules.attendance.ot_bands import hours_maps_sum, minutes_map_to_hours
from app.modules.attendance.timesheet_details import (
    aggregate_month_details,
    leave_days_on_day,
    sync_timesheet_month_details,
    work_days_from_hours,
)
from app.modules.calendar.service import compute_divisor
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload
from app.modules.payroll.attendance_penalty import (
    AttendanceDayPenaltyView,
    LeaveAdjustmentView,
    summarize_attendance_penalties,
)
from app.modules.payroll.money import D
from app.modules.payroll.period_eligibility import employee_on_payroll_period

ZERO = Decimal("0")
Q2 = Decimal("0.01")
Q4 = Decimal("0.0001")

# Đầy đủ 14 mã thật, nguồn Common_Codes.csv nhóm HRAB0110 (22§22.6, hạng mục 2.2). Thay cho
# 8 mã tạm V1 (AL/REM/UL/UA/SICK/MARRIAGE/FUNERAL/HEALTHCHECK) — không khớp mã GenusSuite gốc.
# Cột: code, name, pay_ratio_percent (None=chưa đặt, chỉ PER), paid_by_si, affects_attendance_bonus,
# counts_as_worked_day, requires_document, max_days_per_year.
LEAVE_SEED = [
    ("ALE", "Nghỉ phép năm", 100, False, False, True, False, None),
    ("FLE", "Nghỉ tang chế", 100, False, False, True, True, 3),
    ("WED", "Nghỉ cưới", 100, False, False, True, True, 3),
    ("LA", "Nghỉ tai nạn lao động", 100, False, False, True, True, None),
    ("OFF", "Nghỉ bù", 100, False, False, True, False, None),
    ("TMP", "Nghỉ hết hàng", 70, False, False, False, False, None),
    ("PT", "Nghỉ khám thai", 0, True, False, False, True, None),
    ("MLE", "Nghỉ thai sản", 0, True, False, False, True, None),
    ("MC", "Nghỉ sẩy thai", 0, True, False, False, True, None),
    ("SLE", "Nghỉ ốm", 0, True, False, False, True, None),
    ("SCH", "Nghỉ con ốm", 0, True, False, False, True, None),
    ("NOP", "Nghỉ không phép", 0, False, True, False, False, None),
    ("NON", "Không chấm công", 0, False, True, False, False, None),
    ("PER", "Nghỉ có phép", None, False, False, False, False, None),
]


def _attendance_penalties(db: Session) -> dict:
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        return dict((pkg.payload or {}).get("attendance_penalties") or default_payload()["attendance_penalties"])
    return dict(default_payload()["attendance_penalties"])


def _day_penalty_views(day_rows: list[AttendanceDay]) -> list[AttendanceDayPenaltyView]:
    return [
        AttendanceDayPenaltyView(
            work_date=d.work_date,
            is_workday=bool(d.is_workday),
            leave_code=d.leave_code,
            late_minutes=int(d.late_minutes or 0),
            early_minutes=int(d.early_minutes or 0),
            punch_count=int(d.punch_count or 0),
            first_in=d.first_in,
            last_out=d.last_out,
            worked_hours=D(d.worked_hours),
        )
        for d in day_rows
    ]


def _adj_penalty_views(adj_rows: list[TimesheetAdjustment]) -> list[LeaveAdjustmentView]:
    out: list[LeaveAdjustmentView] = []
    for a in adj_rows:
        if a.kind == "leave" and a.leave_code and a.days is not None and D(a.days) > 0:
            out.append(LeaveAdjustmentView(leave_code=a.leave_code, days=D(a.days)))
    return out


def seed_leave_types(db: Session) -> None:
    added = False
    for code, name, pct, si, bonus, worked, doc, max_days in LEAVE_SEED:
        row = db.get(LeaveType, code)
        if row is None:
            db.add(
                LeaveType(
                    code=code,
                    name=name,
                    paid_by_company=bool(pct) and pct > 0,
                    counts_as_unauthorized=bonus,
                    pay_ratio_percent=pct,
                    paid_by_si=si,
                    affects_attendance_bonus=bonus,
                    counts_as_worked_day=worked,
                    requires_document=doc,
                    max_days_per_year=max_days,
                )
            )
            added = True
    if added:
        db.commit()


def parse_period(period: str) -> tuple[int, int]:
    try:
        y_str, m_str = period.strip().split("-")
        year, month = int(y_str), int(m_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: kỳ lương phải dạng YYYY-MM (ví dụ 2025-10).",
        ) from exc
    if year < 2000 or year > 2100 or month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: năm/tháng kỳ lương không hợp lệ.",
        )
    return year, month


def get_pay_period(db: Session, period: str) -> PayPeriod | None:
    """SELECT kỳ lương — không tạo, không cập nhật. Dùng cho GET."""
    year, month = parse_period(period)
    return (
        db.query(PayPeriod)
        .filter(PayPeriod.year == year, PayPeriod.month == month)
        .one_or_none()
    )


def calendar_month_bounds(period: str) -> tuple[date, date]:
    year, month = parse_period(period)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def employee_ids_with_punches_in_range(db: Session, date_from: date, date_to: date) -> list[UUID]:
    """NV có vân tay trong khoảng — dùng để rebuild bảng công sau ingest, không quét cả nhà máy."""
    from datetime import datetime

    from app.modules.attendance.engine import VN_TZ
    from app.modules.integration.models import AttendancePunch
    from app.modules.mdm.models import Employee

    start = datetime(date_from.year, date_from.month, date_from.day, tzinfo=VN_TZ)
    end = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=VN_TZ)
    codes = [
        code
        for (code,) in db.query(AttendancePunch.employee_code)
        .filter(AttendancePunch.punch_time >= start, AttendancePunch.punch_time <= end)
        .distinct()
        .all()
        if code
    ]
    if not codes:
        return []
    return [eid for (eid,) in db.query(Employee.id).filter(Employee.employee_code.in_(codes)).all()]


def rebuild_timesheets_for_date_window(db: Session, date_from: date, date_to: date) -> None:
    ids = employee_ids_with_punches_in_range(db, date_from, date_to)
    if not ids:
        return
    y, m = date_from.year, date_from.month
    end_y, end_m = date_to.year, date_to.month
    while (y, m) <= (end_y, end_m):
        rebuild_timesheets(db, f"{y:04d}-{m:02d}", recalc_days=False, employee_ids=ids)
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def require_pay_period(db: Session, period: str) -> PayPeriod:
    """GET chi tiết kỳ: có thì trả, chưa có thì 404 — không INSERT."""
    row = get_pay_period(db, period)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Trợ Lý AI: chưa có kỳ lương {period} — "
                "hãy bấm Tính lương (hoặc tổng hợp bảng công) trước."
            ),
        )
    return row


def ensure_pay_period(db: Session, period: str, *, refresh_open: bool = False) -> PayPeriod:
    """Lấy kỳ lương; tạo nếu chưa có. Chỉ dùng trên POST (tính lương, rebuild, phát hành).

    GET không được gọi hàm này — dùng get_pay_period / require_pay_period.
    QA-07: không UPDATE divisor trên đường đọc. Chỉ làm mới khi
    `refresh_open=True` (tính lương, rebuild bảng công).
    """
    year, month = parse_period(period)
    row = get_pay_period(db, period)
    last_day = calendar.monthrange(year, month)[1]
    date_from = date(year, month, 1)
    date_to = date(year, month, last_day)
    # GET (lưới công / timesheet) không tính lại divisor — chỉ khi tạo kỳ mới hoặc rebuild.
    if row is None:
        div = compute_divisor(db, year, month)
        row = PayPeriod(
            year=year,
            month=month,
            date_from=date_from,
            date_to=date_to,
            official_work_days=div.official_work_days,
            salary_divisor=div.salary_divisor,
            status="open",
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            # Ganh dua: nhieu request song song cung tao ky luong 1 thang.
            db.rollback()
            row = (
                db.query(PayPeriod)
                .filter(PayPeriod.year == year, PayPeriod.month == month)
                .one()
            )
        else:
            db.refresh(row)
        return row
    if refresh_open and row.status == "open":
        div = compute_divisor(db, year, month)
        row.official_work_days = div.official_work_days
        row.salary_divisor = div.salary_divisor
        row.date_from = date_from
        row.date_to = date_to
        db.commit()
        db.refresh(row)
    return row


def _assert_open(period: PayPeriod) -> None:
    if period.status == "locked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: kỳ lương đã khóa — không sửa bảng công.",
        )


def _hours(minutes: int) -> Decimal:
    return (Decimal(minutes) / Decimal(60)).quantize(Q2, rounding=ROUND_HALF_UP)


def _purge_ineligible_timesheets(db: Session, pay: PayPeriod) -> int:
    """Xóa dòng công tháng của NV nghỉ trước kỳ (vd. seed 1718)."""
    rows = (
        db.query(TimesheetMonth, Employee)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(TimesheetMonth.pay_period_id == pay.id)
        .all()
    )
    removed = 0
    for ts, emp in rows:
        if not employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            db.delete(ts)
            removed += 1
    if removed:
        db.commit()
    return removed


def rebuild_timesheets(
    db: Session,
    period: str,
    *,
    recalc_days: bool = True,
    employee_id: UUID | None = None,
    employee_ids: Collection[UUID] | None = None,
) -> RebuildTimesheetResult:
    """Tổng hợp bảng công tháng. Có employee_id/ids thì chỉ NV vừa sửa — không quét cả nhà máy."""
    scope: Collection[UUID] | None
    if employee_id is not None:
        scope = (employee_id,)
    elif employee_ids:
        scope = employee_ids
    else:
        scope = None

    pay = ensure_pay_period(db, period, refresh_open=scope is None)
    _assert_open(pay)
    seed_leave_types(db)
    if scope is None:
        _purge_ineligible_timesheets(db, pay)

    if recalc_days:
        from app.modules.attendance.service import recalculate_days

        recalculate_days(db, date_from=pay.date_from, date_to=pay.date_to)

    emp_q = db.query(Employee).filter(Employee.deleted_at.is_(None))
    if scope is not None:
        emp_q = emp_q.filter(Employee.id.in_(scope))
    else:
        emp_q = emp_q.filter(Employee.status == "active")
    employees = emp_q.all()
    days_q = db.query(AttendanceDay).filter(
        AttendanceDay.work_date >= pay.date_from,
        AttendanceDay.work_date <= pay.date_to,
    )
    if scope is not None:
        days_q = days_q.filter(AttendanceDay.employee_id.in_(scope))
    days = days_q.all()
    by_emp_days: dict[UUID, list[AttendanceDay]] = {}
    for d in days:
        by_emp_days.setdefault(d.employee_id, []).append(d)

    adj_q = db.query(TimesheetAdjustment).filter(TimesheetAdjustment.pay_period_id == pay.id)
    if scope is not None:
        adj_q = adj_q.filter(TimesheetAdjustment.employee_id.in_(scope))
    adjustments = adj_q.all()
    by_emp_adj: dict[UUID, list[TimesheetAdjustment]] = {}
    for a in adjustments:
        by_emp_adj.setdefault(a.employee_id, []).append(a)

    # Nhân sự có punch/điều chỉnh nhưng không active vẫn đưa vào nếu có dữ liệu
    emp_ids = {e.id for e in employees}
    for eid in set(by_emp_days) | set(by_emp_adj):
        emp_ids.add(eid)
    emp_map = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()} if emp_ids else {}

    penalty_rules = _attendance_penalties(db)
    upserted = 0
    for emp_id, emp in emp_map.items():
        if emp.deleted_at is not None:
            continue
        if not employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            continue
        day_rows = by_emp_days.get(emp_id, [])
        adj_rows = by_emp_adj.get(emp_id, [])

        # Không có punch + không có điều chỉnh → giữ nguyên dòng timesheet
        # (tránh xóa công đã import từ Excel test / nhập tay).
        if not day_rows and not adj_rows:
            existing = (
                db.query(TimesheetMonth)
                .filter(
                    TimesheetMonth.pay_period_id == pay.id,
                    TimesheetMonth.employee_id == emp_id,
                )
                .one_or_none()
            )
            if existing is not None:
                continue

        worked = ZERO
        late_c = 0
        early_c = 0
        ot_w = ZERO
        ot_ext = ZERO
        ot_we = ZERO
        ot_h = ZERO
        on_books_by_rate: dict[str, Decimal] = {}
        external_by_rate: dict[str, Decimal] = {}
        for d in day_rows:
            leave_d = leave_days_on_day(d)
            hours = Decimal(d.worked_hours or 0)
            if d.is_workday and hours > 0:
                if leave_d >= 1:
                    pass
                else:
                    # Phiếu lương: ngày công = giờ công / 8 (4h chiều = 0.5; 3.42h = 0.4275).
                    worked += work_days_from_hours(hours)
            if d.ot_on_books_minutes > 0:
                ot_w += _hours(d.ot_on_books_minutes)
            # OT ngoài = ngày thường ngoài sổ + CN + lễ (cột «Tăng ca ngoài» gồm cả CN/lễ)
            if d.ot_type == "weekend" and (d.ot_minutes or 0) > 0:
                h = _hours(d.ot_minutes)
                ot_we += h
                ot_ext += h
            elif d.ot_type == "holiday" and (d.ot_minutes or 0) > 0:
                h = _hours(d.ot_minutes)
                ot_h += h
                ot_ext += h
            elif (d.ot_external_minutes or 0) > 0:
                ot_ext += _hours(d.ot_external_minutes)

            raw_rates = d.ot_rate_minutes if isinstance(getattr(d, "ot_rate_minutes", None), dict) else {}
            if raw_rates:
                on_books_by_rate = hours_maps_sum(
                    on_books_by_rate, minutes_map_to_hours(raw_rates.get("on_books") or {})
                )
                external_by_rate = hours_maps_sum(
                    external_by_rate, minutes_map_to_hours(raw_rates.get("external") or {})
                )
            elif (d.ot_minutes or 0) > 0:
                if d.ot_on_books_minutes:
                    on_books_by_rate = hours_maps_sum(
                        on_books_by_rate, {"1.5": _hours(d.ot_on_books_minutes)}
                    )
                if d.ot_type == "weekend":
                    external_by_rate = hours_maps_sum(external_by_rate, {"2.0": _hours(d.ot_minutes)})
                elif d.ot_type == "holiday":
                    external_by_rate = hours_maps_sum(external_by_rate, {"3.0": _hours(d.ot_minutes)})
                elif d.ot_external_minutes:
                    external_by_rate = hours_maps_sum(
                        external_by_rate, {"1.5": _hours(d.ot_external_minutes)}
                    )

        penalty_sum = summarize_attendance_penalties(
            _day_penalty_views(day_rows),
            _adj_penalty_views(adj_rows),
            contract_signed_at=emp.contract_signed_at,
            penalties=penalty_rules,
        )
        late_c = penalty_sum.late_count
        early_c = penalty_sum.early_count

        rem = ZERO
        for a in adj_rows:
            if a.kind == "ot" and a.ot_hours is not None:
                h = Decimal(a.ot_hours)
                if a.ot_type == "weekend":
                    ot_we += h
                    ot_ext += h
                    external_by_rate = hours_maps_sum(external_by_rate, {"2.0": h})
                elif a.ot_type == "holiday":
                    ot_h += h
                    ot_ext += h
                    external_by_rate = hours_maps_sum(external_by_rate, {"3.0": h})
                else:
                    ot_w += h
                    on_books_by_rate = hours_maps_sum(on_books_by_rate, {"1.5": h})

        buckets = aggregate_month_details(day_rows, adj_rows, emp)
        # Phép năm trên lưới ngày (leave_code=ALE) + điều chỉnh — cùng nguồn với chi tiết ABS_ALE.
        al = ZERO
        for (_seg, cat), vals in buckets.items():
            if cat == "ABS_ALE":
                al += vals["days"]

        row = (
            db.query(TimesheetMonth)
            .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp_id)
            .one_or_none()
        )
        if row is None:
            row = TimesheetMonth(pay_period_id=pay.id, employee_id=emp_id)
            db.add(row)
        row.worked_days = worked.quantize(Q4, rounding=ROUND_HALF_UP).quantize(Q2, rounding=ROUND_DOWN)
        row.al_days = al.quantize(Q4)
        row.rem_days = rem.quantize(Q4)
        row.late_count = late_c
        row.early_count = early_c
        row.ot_hours_weekday = ot_w.quantize(Q2)
        row.ot_hours_external = ot_ext.quantize(Q2)
        row.ot_hours_weekend = ot_we.quantize(Q2)
        row.ot_hours_holiday = ot_h.quantize(Q2)
        row.ot_hours_by_rate = {
            "on_books": {k: str(v.quantize(Q2)) for k, v in on_books_by_rate.items() if v},
            "external": {k: str(v.quantize(Q2)) for k, v in external_by_rate.items() if v},
        }
        db.flush()
        sync_timesheet_month_details(db, row.id, buckets)
        upserted += 1

    db.commit()
    return RebuildTimesheetResult(
        period=f"{pay.year:04d}-{pay.month:02d}",
        pay_period_id=pay.id,
        rows_upserted=upserted,
        message=f"Đã tổng hợp bảng công {pay.month:02d}/{pay.year} cho {upserted} nhân viên.",
    )


def list_timesheets(db: Session, period: str) -> list[TimesheetMonthOut]:
    pay = get_pay_period(db, period)
    if pay is None:
        return []
    rows = (
        db.query(TimesheetMonth, Employee)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(TimesheetMonth.pay_period_id == pay.id)
        .order_by(Employee.employee_code)
        .all()
    )
    out: list[TimesheetMonthOut] = []
    for ts, emp in rows:
        if not employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            continue
        out.append(
            TimesheetMonthOut(
                id=ts.id,
                pay_period_id=ts.pay_period_id,
                period=f"{pay.year:04d}-{pay.month:02d}",
                employee_id=emp.id,
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                worked_days=ts.worked_days,
                al_days=ts.al_days,
                rem_days=ts.rem_days,
                late_count=ts.late_count,
                early_count=ts.early_count,
                ot_hours_weekday=ts.ot_hours_weekday,
                ot_hours_external=ts.ot_hours_external,
                ot_hours_weekend=ts.ot_hours_weekend,
                ot_hours_holiday=ts.ot_hours_holiday,
                ot_hours_by_rate=getattr(ts, "ot_hours_by_rate", None) or {},
            )
        )
    return out


def list_timesheet_details(
    db: Session,
    period: str,
    employee_code: str | None = None,
) -> list[TimesheetMonthDetailOut]:
    pay = get_pay_period(db, period)
    if pay is None:
        return []
    q = (
        db.query(TimesheetMonthDetail, TimesheetMonth, Employee)
        .join(TimesheetMonth, TimesheetMonth.id == TimesheetMonthDetail.timesheet_month_id)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(TimesheetMonth.pay_period_id == pay.id)
        .order_by(Employee.employee_code, TimesheetMonthDetail.category, TimesheetMonthDetail.segment)
    )
    if employee_code:
        q = q.filter(Employee.employee_code == employee_code.strip())
    out: list[TimesheetMonthDetailOut] = []
    period_str = f"{pay.year:04d}-{pay.month:02d}"
    for detail, ts, emp in q.all():
        if not employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            continue
        out.append(
            TimesheetMonthDetailOut(
                id=detail.id,
                timesheet_month_id=ts.id,
                period=period_str,
                employee_id=emp.id,
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                category=detail.category,
                segment=detail.segment,
                hours=detail.hours,
                days=detail.days,
            )
        )
    return out


def get_pay_period_out(db: Session, period: str) -> PayPeriodOut:
    pay = require_pay_period(db, period)
    return PayPeriodOut.model_validate(pay)


def list_leave_types(db: Session) -> list[LeaveTypeOut]:
    """GET danh mục nghỉ — chỉ SELECT. Seed lúc `python -m app.scripts.seed` / POST."""
    rows = db.query(LeaveType).order_by(LeaveType.code).all()
    return [LeaveTypeOut.model_validate(r) for r in rows]


def create_adjustment(db: Session, body: AdjustmentCreate, user: User) -> AdjustmentOut:
    pay = ensure_pay_period(db, body.period)
    _assert_open(pay)
    seed_leave_types(db)

    emp = (
        db.query(Employee)
        .filter(Employee.employee_code == body.employee_code.strip(), Employee.deleted_at.is_(None))
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI: không tìm thấy MSNV {body.employee_code}.",
        )

    kind = body.kind.strip().lower()
    if kind not in ("leave", "ot"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: kind phải là leave hoặc ot.",
        )

    leave_code = None
    days = None
    ot_type = None
    ot_hours = None
    if kind == "leave":
        if not body.leave_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: nghỉ phép cần leave_code.",
            )
        lt = db.get(LeaveType, body.leave_code.strip().upper())
        if lt is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trợ Lý AI: mã nghỉ {body.leave_code} không có trong danh mục.",
            )
        if body.days is None or Decimal(body.days) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: số ngày nghỉ phải > 0.",
            )
        leave_code = lt.code
        days = Decimal(body.days).quantize(Q4)
    else:
        ot_type = (body.ot_type or "weekday").strip().lower()
        if ot_type not in ("weekday", "weekend", "holiday"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: ot_type phải là weekday / weekend / holiday.",
            )
        if body.ot_hours is None or Decimal(body.ot_hours) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: giờ OT nhập tay phải > 0.",
            )
        ot_hours = Decimal(body.ot_hours).quantize(Q2)

    row = TimesheetAdjustment(
        pay_period_id=pay.id,
        employee_id=emp.id,
        kind=kind,
        leave_code=leave_code,
        days=days,
        ot_type=ot_type,
        ot_hours=ot_hours,
        note=(body.note or "").strip(),
        created_by_user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    rebuild_timesheets(db, body.period, recalc_days=False, employee_id=emp.id)
    from app.modules.audit.service import write_audit

    write_audit(
        db,
        actor=user,
        action="attendance.adjust.create",
        entity_type="timesheet_adjustment",
        entity_id=str(row.id),
        summary=f"Nhập tay {kind} cho {emp.employee_code} kỳ {body.period}",
        meta={
            "kind": kind,
            "leave_code": leave_code,
            "days": str(days) if days is not None else None,
            "ot_type": ot_type,
            "ot_hours": str(ot_hours) if ot_hours is not None else None,
        },
    )
    return _adj_out(db, row, emp, user)


def list_adjustments(db: Session, period: str, employee_code: str | None = None) -> list[AdjustmentOut]:
    pay = get_pay_period(db, period)
    if pay is None:
        return []
    q = (
        db.query(TimesheetAdjustment, Employee, User)
        .join(Employee, Employee.id == TimesheetAdjustment.employee_id)
        .join(User, User.id == TimesheetAdjustment.created_by_user_id)
        .filter(TimesheetAdjustment.pay_period_id == pay.id)
        .order_by(TimesheetAdjustment.created_at.desc())
    )
    if employee_code:
        q = q.filter(Employee.employee_code == employee_code.strip())
    return [_adj_out(db, a, e, u) for a, e, u in q.all()]


def delete_adjustment(db: Session, adjustment_id: UUID, user: User) -> dict:
    row = db.get(TimesheetAdjustment, adjustment_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy điều chỉnh.",
        )
    pay = db.get(PayPeriod, row.pay_period_id)
    assert pay is not None
    _assert_open(pay)
    period = f"{pay.year:04d}-{pay.month:02d}"
    emp = db.get(Employee, row.employee_id)
    meta = {
        "kind": row.kind,
        "leave_code": row.leave_code,
        "employee_code": emp.employee_code if emp else None,
    }
    adj_id = str(row.id)
    db.delete(row)
    db.commit()
    rebuild_timesheets(db, period, recalc_days=False, employee_id=row.employee_id)
    from app.modules.audit.service import write_audit

    write_audit(
        db,
        actor=user,
        action="attendance.adjust.delete",
        entity_type="timesheet_adjustment",
        entity_id=adj_id,
        summary=f"Xóa điều chỉnh {meta.get('kind')} kỳ {period}",
        meta=meta,
    )
    return {"ok": True, "message": f"Đã xóa điều chỉnh (bởi {user.username}).", "period": period}


def _adj_out(db: Session, row: TimesheetAdjustment, emp: Employee, user: User) -> AdjustmentOut:
    pay = db.get(PayPeriod, row.pay_period_id)
    period = f"{pay.year:04d}-{pay.month:02d}" if pay else ""
    return AdjustmentOut(
        id=row.id,
        period=period,
        employee_id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        kind=row.kind,
        leave_code=row.leave_code,
        days=row.days,
        ot_type=row.ot_type,
        ot_hours=row.ot_hours,
        note=row.note,
        created_by=user.username,
        created_at=row.created_at,
    )
