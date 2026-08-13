"""3.4 — gán cột mở rộng attendance_days sau calculate_day."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.attendance.engine import DayCalcResult
from app.modules.attendance.models import AttendanceDay, TeamShiftSchedule
from app.modules.attendance.seed_shifts import ADMIN_SHIFT_CODE, assign_default_shift_to_teams
from app.modules.attendance.shifts_service import get_effective_shift
from app.modules.mdm.models import Employee, Team

Q2 = Decimal("0.01")


def resolve_segment(employee: Employee) -> str:
    """22§22.4 — probation | official."""
    return "probation" if employee.status == "probation" else "official"


def build_shift_cache(
    db: Session,
    team_ids: set[UUID],
    work_dates: set[date],
) -> dict[tuple[UUID, date], str]:
    """Prefetch ca làm việc — tránh N+1 get_effective_shift trong recalc."""
    if not team_ids or not work_dates:
        return {}
    assign_default_shift_to_teams(db)
    teams = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}
    overrides = (
        db.query(TeamShiftSchedule)
        .filter(
            TeamShiftSchedule.team_id.in_(team_ids),
            TeamShiftSchedule.work_date.in_(work_dates),
        )
        .all()
    )
    override_map = {(o.team_id, o.work_date): o.work_shift_id for o in overrides}
    cache: dict[tuple[UUID, date], str] = {}
    for team_id in team_ids:
        team = teams.get(team_id)
        if team is None:
            continue
        for wd in work_dates:
            key = (team_id, wd)
            if key in override_map:
                cache[key] = override_map[key]
            elif team.default_shift_id:
                cache[key] = team.default_shift_id
            else:
                cache[key] = ADMIN_SHIFT_CODE
    return cache


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
