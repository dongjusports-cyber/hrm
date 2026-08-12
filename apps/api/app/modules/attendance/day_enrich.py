"""3.4 — gán cột mở rộng attendance_days sau calculate_day."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.modules.attendance.engine import DayCalcResult
from app.modules.attendance.models import AttendanceDay
from app.modules.attendance.seed_shifts import ADMIN_SHIFT_CODE
from app.modules.attendance.shifts_service import get_effective_shift
from app.modules.mdm.models import Employee

Q2 = Decimal("0.01")


def resolve_segment(employee: Employee) -> str:
    """22§22.4 — probation | official."""
    return "probation" if employee.status == "probation" else "official"


def resolve_work_shift_id(db: Session, employee: Employee, work_date: date) -> str:
    if employee.team_id is None:
        return ADMIN_SHIFT_CODE
    eff = get_effective_shift(db, employee.team_id, work_date)
    return eff.work_shift_id or ADMIN_SHIFT_CODE


def _hours_from_ot_minutes(minutes: int) -> Decimal:
    if minutes <= 0:
        return Decimal("0")
    return (Decimal(minutes) / Decimal("60")).quantize(Q2, rounding=ROUND_HALF_UP)


def apply_calc_to_day_row(
    row: AttendanceDay,
    *,
    calc: DayCalcResult,
    employee: Employee,
    work_shift_id: str,
) -> None:
    """Ghi kết quả máy chấm + metadata 3.4 (không đụng is_locked / note / leave_code thủ công)."""
    row.first_in = calc.first_in
    row.last_out = calc.last_out
    row.worked_hours = calc.worked_hours
    row.late_minutes = calc.late_minutes
    row.early_minutes = calc.early_minutes
    row.ot_minutes = calc.ot_minutes
    row.ot_on_books_minutes = calc.ot_on_books_minutes
    row.ot_external_minutes = calc.ot_external_minutes
    row.ot_type = calc.ot_type
    row.punch_count = calc.punch_count
    row.is_workday = calc.is_workday
    row.work_shift_id = work_shift_id
    row.source = "machine"
    row.segment = resolve_segment(employee)
    row.night_hours = Decimal("0")
    row.ot_night_hours = Decimal("0")
    row.sunday_hours = Decimal("0")
    row.holiday_hours = Decimal("0")
    ot_h = _hours_from_ot_minutes(calc.ot_minutes)
    if calc.ot_type == "weekend":
        row.sunday_hours = ot_h
    elif calc.ot_type == "holiday":
        row.holiday_hours = ot_h
