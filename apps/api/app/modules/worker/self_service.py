"""Worker self-service — công tháng, số dư phép năm."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.attendance.annual_leave_ledger import (
    annual_leave_remaining,
    entitled_days_for,
    pending_submitted_days,
    sync_accrual,
)
from app.modules.attendance.engine import VN_TZ, to_vn
from app.modules.attendance.models import AttendanceDay, PayPeriod, TimesheetMonth
from app.modules.attendance.service import list_days
from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.core.models import User
from app.modules.integration.models import AttendancePunch
from app.modules.integration.service import is_patrol_guard_code
from app.modules.mdm.models import Employee
from app.modules.worker import service as worker_service
from app.modules.worker.schemas import (
    WorkerAttendanceDayOut,
    WorkerAttendanceMonthOut,
    WorkerLeaveBalanceOut,
)


def _require_employee(db: Session, worker: User) -> Employee:
    emp = worker_service._employee_for_user(db, worker)
    if emp is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy hồ sơ nhân viên.")
    return emp


def get_leave_balance(db: Session, worker: User, as_of: date | None = None) -> WorkerLeaveBalanceOut:
    emp = _require_employee(db, worker)
    as_of = as_of or date.today()
    ledger = sync_accrual(db, emp, as_of)
    pending = pending_submitted_days(db, emp.id, as_of.year)
    remaining = annual_leave_remaining(db, emp.id, as_of)
    days_per_year = entitled_days_for(db, emp, as_of)
    return WorkerLeaveBalanceOut(
        year=as_of.year,
        days_per_year=days_per_year,
        accrued=ledger.accrued,
        used=ledger.used,
        pending_submitted=pending,
        remaining=remaining,
    )


def _punches_on_date(db: Session, emp: Employee, work_date: date) -> list[datetime]:
    """Mốc chấm thô từ máy — giữ nguyên giây, không làm tròn ca 08–17."""
    if is_patrol_guard_code(emp.employee_code):
        return []
    start = datetime(work_date.year, work_date.month, work_date.day, tzinfo=VN_TZ) - timedelta(hours=1)
    end = start + timedelta(days=1, hours=2)
    rows = (
        db.query(AttendancePunch.punch_time)
        .filter(
            AttendancePunch.employee_code == emp.employee_code,
            AttendancePunch.punch_time >= start,
            AttendancePunch.punch_time < end,
        )
        .order_by(AttendancePunch.punch_time)
        .all()
    )
    return [to_vn(pt) for (pt,) in rows if to_vn(pt).date() == work_date]


def get_attendance_month(db: Session, worker: User, period: str) -> WorkerAttendanceMonthOut:
    emp = _require_employee(db, worker)
    pay: PayPeriod = ensure_pay_period(db, period)
    ts = (
        db.query(TimesheetMonth)
        .filter(
            TimesheetMonth.pay_period_id == pay.id,
            TimesheetMonth.employee_id == emp.id,
        )
        .one_or_none()
    )
    days = list_days(db, pay.date_from, pay.date_to, employee_code=emp.employee_code)
    by_date = {d.work_date: d for d in days}
    day_rows = (
        db.query(AttendanceDay)
        .filter(
            AttendanceDay.employee_id == emp.id,
            AttendanceDay.work_date >= pay.date_from,
            AttendanceDay.work_date <= pay.date_to,
        )
        .order_by(AttendanceDay.work_date)
        .all()
    )
    worked_from_days = sum(
        1 for d in day_rows if (d.worked_hours or Decimal("0")) > 0 or d.leave_code
    )
    day_out: list[WorkerAttendanceDayOut] = []
    cur = pay.date_from
    while cur <= pay.date_to:
        d = by_date.get(cur)
        punches = _punches_on_date(db, emp, cur)
        if d is not None:
            day_out.append(
                WorkerAttendanceDayOut(
                    work_date=d.work_date,
                    first_in=d.first_in,
                    last_out=d.last_out,
                    worked_hours=d.worked_hours,
                    late_minutes=d.late_minutes,
                    early_minutes=d.early_minutes,
                    leave_code=d.leave_code,
                    punch_count=d.punch_count,
                    is_workday=d.is_workday,
                    punches=punches,
                )
            )
        elif punches:
            day_out.append(
                WorkerAttendanceDayOut(
                    work_date=cur,
                    first_in=punches[0],
                    last_out=punches[-1] if len(punches) > 1 else None,
                    worked_hours=Decimal("0"),
                    late_minutes=0,
                    early_minutes=0,
                    leave_code=None,
                    punch_count=len(punches),
                    is_workday=True,
                    punches=punches,
                )
            )
        cur = cur.fromordinal(cur.toordinal() + 1)
    return WorkerAttendanceMonthOut(
        period=f"{pay.year:04d}-{pay.month:02d}",
        date_from=pay.date_from,
        date_to=pay.date_to,
        worked_days=ts.worked_days if ts else Decimal(str(worked_from_days)),
        al_days=ts.al_days if ts else Decimal("0"),
        rem_days=ts.rem_days if ts else Decimal("0"),
        late_count=ts.late_count if ts else sum(1 for d in day_rows if d.late_minutes > 0),
        days=day_out,
    )
