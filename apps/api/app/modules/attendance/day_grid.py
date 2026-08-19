"""3.7 — lưới bảng công một ngày + sửa/bulk (23§94–96)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.day_enrich import (
    apply_calc_to_day_row,
    resolve_work_shift_id,
    wt_hours_early_on,
)
from app.modules.attendance.engine import VN_TZ, calculate_day, combine_vn, to_vn
from app.modules.attendance.models import AttendanceDay, LeaveType, WorkShift
from app.modules.attendance.shift_schedule import engine_ot_kwargs, timing_from_shift
from app.modules.attendance.schemas import AttendanceDayGridOut, AttendanceDayOut
from app.modules.attendance.ot_split import load_ot_split_policy
from app.modules.attendance.service import _load_schedule, list_days
from app.modules.attendance.timesheet import _assert_open, ensure_pay_period, rebuild_timesheets, seed_leave_types
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.integration.models import AttendancePunch
from app.modules.mdm.models import Department, Employee, Team

ACTIVE_EMP = ("active", "probation")


def ensure_manual_punches(
    db: Session,
    emp: Employee,
    first_in: datetime | None,
    last_out: datetime | None,
) -> None:
    """Ghi giờ HR sửa vào attendance_punches — tính lương/recalc không nuốt mốc tay."""
    candidates: list[tuple[datetime, str]] = []
    if first_in is not None:
        candidates.append((to_vn(first_in), "IN"))
    if last_out is not None:
        lo = to_vn(last_out)
        if not candidates or lo != candidates[0][0]:
            candidates.append((lo, "OUT"))
    if not candidates:
        return
    day = candidates[0][0].date()
    existing = (
        db.query(AttendancePunch)
        .filter(
            AttendancePunch.employee_code == emp.employee_code,
            AttendancePunch.punch_time >= combine_vn(day, time.min),
            AttendancePunch.punch_time <= combine_vn(day, time(23, 59, 59)),
        )
        .all()
    )
    seen = {int(to_vn(p.punch_time).timestamp()) for p in existing}
    for t, direction in candidates:
        if int(t.timestamp()) in seen:
            continue
        db.add(
            AttendancePunch(
                employee_code=emp.employee_code,
                employee_id=emp.id,
                punch_time=t,
                direction=direction,
                source="manual",
            )
        )
        seen.add(int(t.timestamp()))


def _day_to_out(day: AttendanceDay, emp: Employee) -> AttendanceDayOut:
    return AttendanceDayOut(
        id=day.id,
        employee_id=day.employee_id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        work_date=day.work_date,
        first_in=to_vn(day.first_in) if day.first_in else None,
        last_out=to_vn(day.last_out) if day.last_out else None,
        worked_hours=day.worked_hours,
        late_minutes=day.late_minutes,
        early_minutes=day.early_minutes,
        ot_minutes=day.ot_minutes,
        ot_on_books_minutes=day.ot_on_books_minutes,
        ot_external_minutes=day.ot_external_minutes,
        ot_type=day.ot_type,
        punch_count=day.punch_count,
        is_workday=day.is_workday,
        work_shift_id=day.work_shift_id,
        leave_code=day.leave_code,
        source=day.source,
        night_hours=day.night_hours,
        sunday_hours=day.sunday_hours,
        holiday_hours=day.holiday_hours,
        ot_night_hours=day.ot_night_hours,
        segment=day.segment,
        is_locked=day.is_locked,
        note=day.note,
        cycle_leave=bool(day.cycle_leave),
        edited_by_user_id=day.edited_by_user_id,
        edited_at=to_vn(day.edited_at) if day.edited_at else None,
    )


def _needs_action(day: AttendanceDay | None, work_date: date, schedule) -> bool:
    from app.modules.attendance.engine import is_company_workday

    if day is None:
        return is_company_workday(work_date, schedule)
    if day.is_locked:
        return False
    incomplete = bool(day.first_in) ^ bool(day.last_out)
    if day.late_minutes > 0 or day.early_minutes > 0:
        return True
    if incomplete or (day.punch_count > 0 and day.punch_count % 2 == 1):
        return True
    if day.is_workday and day.punch_count == 0 and not day.leave_code:
        return True
    return False


def _row_flag(day: AttendanceDay | None, work_date: date, schedule) -> str:
    if day is None:
        return "empty"
    if day.is_locked:
        return "locked"
    if day.late_minutes > 0 and day.early_minutes > 0:
        return "both"
    if day.late_minutes > 0:
        return "late"
    if day.early_minutes > 0:
        return "early"
    incomplete = bool(day.first_in) ^ bool(day.last_out)
    if incomplete or (day.punch_count > 0 and day.punch_count % 2 == 1):
        return "odd"
    if day.is_workday and day.punch_count == 0 and not day.leave_code:
        return "missing"
    return "ok"


def list_days_grid(
    db: Session,
    work_date: date,
    *,
    needs_action_only: bool = False,
    department_id: UUID | None = None,
) -> list[AttendanceDayGridOut]:
    schedule = _load_schedule(db)

    employees = (
        db.query(Employee, Team, Department)
        .outerjoin(Team, Team.id == Employee.team_id)
        .outerjoin(Department, Department.id == Team.department_id)
        .filter(Employee.deleted_at.is_(None), Employee.status.in_(ACTIVE_EMP))
        .order_by(Employee.employee_code)
        .all()
    )
    day_rows = (
        db.query(AttendanceDay)
        .filter(AttendanceDay.work_date == work_date)
        .all()
    )
    by_emp = {d.employee_id: d for d in day_rows}

    out: list[AttendanceDayGridOut] = []
    for emp, team, dept in employees:
        if department_id is not None and (dept is None or dept.id != department_id):
            continue
        day = by_emp.get(emp.id)
        needs = _needs_action(day, work_date, schedule)
        if needs_action_only and not needs:
            continue
        if day is None:
            out.append(
                AttendanceDayGridOut(
                    id=None,
                    employee_id=emp.id,
                    employee_code=emp.employee_code,
                    full_name=emp.full_name,
                    work_date=work_date,
                    first_in=None,
                    last_out=None,
                    worked_hours=0,
                    late_minutes=0,
                    early_minutes=0,
                    ot_minutes=0,
                    ot_type=None,
                    punch_count=0,
                    is_workday=True,
                    team_code=team.code if team else None,
                    team_name=team.name if team else None,
                    department_code=dept.code if dept else None,
                    department_name=dept.name if dept else None,
                    needs_action=needs,
                    row_flag=_row_flag(None, work_date, schedule),
                )
            )
        else:
            row_out = _day_to_out(day, emp)
            out.append(
                AttendanceDayGridOut(
                    **row_out.model_dump(),
                    team_code=team.code if team else None,
                    team_name=team.name if team else None,
                    department_code=dept.code if dept else None,
                    department_name=dept.name if dept else None,
                    needs_action=needs,
                    row_flag=_row_flag(day, work_date, schedule),
                )
            )
    return out


def _assert_day_editable(db: Session, work_date: date) -> None:
    pay = ensure_pay_period(db, f"{work_date.year:04d}-{work_date.month:02d}")
    _assert_open(pay)


def _get_employee(db: Session, employee_code: str) -> Employee:
    emp = (
        db.query(Employee)
        .filter(Employee.employee_code == employee_code.strip(), Employee.deleted_at.is_(None))
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI: không tìm thấy MSNV {employee_code}.",
        )
    return emp


def _get_or_create_day(db: Session, emp: Employee, work_date: date) -> AttendanceDay:
    row = (
        db.query(AttendanceDay)
        .filter(AttendanceDay.employee_id == emp.id, AttendanceDay.work_date == work_date)
        .one_or_none()
    )
    if row is None:
        row = AttendanceDay(employee_id=emp.id, work_date=work_date)
        db.add(row)
    if row.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: ngày công {work_date} của {emp.employee_code} đã khóa — không sửa.",
        )
    return row


def patch_day_cell(
    db: Session,
    user: User,
    *,
    employee_code: str,
    work_date: date,
    first_in: datetime | None = None,
    last_out: datetime | None = None,
    leave_code: str | None = None,
    note: str | None = None,
    clear_note: bool = False,
    clear_times: bool = False,
    clear_first_in: bool = False,
    clear_last_out: bool = False,
) -> AttendanceDayOut:
    _assert_day_editable(db, work_date)
    seed_leave_types(db)
    emp = _get_employee(db, employee_code)
    row = _get_or_create_day(db, emp, work_date)
    schedule = _load_schedule(db)

    if leave_code is not None:
        code = leave_code.strip().upper() if leave_code else None
        if code:
            lt = db.get(LeaveType, code)
            if lt is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Trợ Lý AI: mã nghỉ {leave_code} không có trong danh mục.",
                )
            row.leave_code = lt.code
        else:
            row.leave_code = None

    if clear_note:
        row.note = ""
    elif note is not None:
        row.note = note.strip()

    if clear_times:
        clear_first_in = True
        clear_last_out = True
    times_requested = first_in is not None or last_out is not None
    clearing = clear_first_in or clear_last_out

    leave_or_note = leave_code is not None or note is not None or clear_note
    if leave_or_note and not times_requested and not clearing:
        row.source = "manual"
        row.edited_by_user_id = user.id
        row.edited_at = datetime.now(tz=VN_TZ)

    if times_requested or clearing:
        if clear_first_in:
            fi = None
        elif first_in is not None:
            fi = to_vn(first_in)
        else:
            fi = to_vn(row.first_in) if row.first_in else None
        if clear_last_out:
            lo = None
        elif last_out is not None:
            lo = to_vn(last_out)
        else:
            lo = to_vn(row.last_out) if row.last_out else None
        punches: list[datetime] = []
        if fi is not None:
            punches.append(fi)
        if lo is not None and lo != fi:
            punches.append(lo)
        shift_id = resolve_work_shift_id(db, emp, work_date)
        timing = timing_from_shift(db.get(WorkShift, shift_id), schedule)
        calc = calculate_day(
            punches,
            work_date,
            timing.schedule,
            ot_split=load_ot_split_policy(db),
            wt_hours_early=wt_hours_early_on(db, emp.id, work_date),
            explicit_pair=True,
            **engine_ot_kwargs(timing),
        )
        apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=shift_id)
        row.source = "manual"
        row.edited_by_user_id = user.id
        row.edited_at = datetime.now(tz=VN_TZ)
        ensure_manual_punches(db, emp, fi, lo)
        if note is not None and not clear_note:
            row.note = note.strip()

    db.commit()
    db.refresh(row)
    period = f"{work_date.year:04d}-{work_date.month:02d}"
    rebuild_timesheets(db, period, recalc_days=False, employee_id=emp.id)
    write_audit(
        db,
        actor=user,
        action="attendance.day.cell",
        entity_type="attendance_day",
        entity_id=str(row.id),
        summary=f"Sửa ô công {emp.employee_code} ngày {work_date.isoformat()}",
        meta={"employee_code": emp.employee_code, "work_date": work_date.isoformat()},
    )
    listed = list_days(db, work_date, work_date, emp.employee_code)
    return listed[0]


def bulk_patch_days(
    db: Session,
    user: User,
    *,
    work_date: date,
    employee_codes: list[str],
    action: str,
    leave_code: str | None = None,
    first_in_time: time | None = None,
    last_out_time: time | None = None,
    note: str | None = None,
    preview: bool = False,
) -> dict:
    """23§23.5 — xem trước hoặc ghi một giao dịch."""
    if action not in ("set_leave", "set_times", "clear_note"):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: action không hợp lệ.")
    if not employee_codes:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: chọn ít nhất một nhân viên.")

    _assert_day_editable(db, work_date)
    seed_leave_types(db)
    schedule = _load_schedule(db)
    lt_code = None
    if action == "set_leave":
        if not leave_code:
            raise HTTPException(status_code=400, detail="Trợ Lý AI: cần leave_code.")
        lt_code = leave_code.strip().upper()
        if db.get(LeaveType, lt_code) is None:
            raise HTTPException(status_code=400, detail=f"Trợ Lý AI: mã nghỉ {leave_code} không hợp lệ.")
    if action == "set_times":
        if first_in_time is None or last_out_time is None:
            raise HTTPException(status_code=400, detail="Trợ Lý AI: cần giờ vào và giờ ra.")

    affected: list[str] = []
    skipped: list[dict] = []
    affected_ids: list[UUID] = []
    for code in employee_codes:
        emp = (
            db.query(Employee)
            .filter(Employee.employee_code == code.strip(), Employee.deleted_at.is_(None))
            .one_or_none()
        )
        if emp is None:
            skipped.append({"employee_code": code, "reason": "Không tìm thấy MSNV."})
            continue
        row = (
            db.query(AttendanceDay)
            .filter(AttendanceDay.employee_id == emp.id, AttendanceDay.work_date == work_date)
            .one_or_none()
        )
        if row is not None and row.is_locked:
            skipped.append({"employee_code": emp.employee_code, "reason": "Dòng đã khóa."})
            continue
        affected.append(emp.employee_code)
        affected_ids.append(emp.id)

    msg = f"Sẽ đổi {len(affected)} dòng"
    if skipped:
        msg += f", bỏ qua {len(skipped)} dòng."
    else:
        msg += "."

    if preview or not affected:
        return {
            "preview": True,
            "affected_count": len(affected),
            "skipped": skipped,
            "message": msg,
        }

    try:
        for code in affected:
            emp = _get_employee(db, code)
            row = _get_or_create_day(db, emp, work_date)
            if action == "set_leave":
                assert lt_code
                row.leave_code = lt_code
                row.source = "manual"
                row.edited_by_user_id = user.id
                row.edited_at = datetime.now(tz=VN_TZ)
            elif action == "clear_note":
                row.note = ""
                row.edited_by_user_id = user.id
                row.edited_at = datetime.now(tz=VN_TZ)
            elif action == "set_times":
                assert first_in_time and last_out_time
                fi = combine_vn(work_date, first_in_time)
                lo = combine_vn(work_date, last_out_time)
                shift_id = resolve_work_shift_id(db, emp, work_date)
                timing = timing_from_shift(db.get(WorkShift, shift_id), schedule)
                calc = calculate_day(
                    [fi, lo],
                    work_date,
                    timing.schedule,
                    ot_split=load_ot_split_policy(db),
                    wt_hours_early=wt_hours_early_on(db, emp.id, work_date),
                    explicit_pair=True,
                    **engine_ot_kwargs(timing),
                )
                apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=shift_id)
                row.source = "manual"
                row.edited_by_user_id = user.id
                row.edited_at = datetime.now(tz=VN_TZ)
                ensure_manual_punches(db, emp, fi, lo)
                if note:
                    row.note = note.strip()
        db.commit()
    except Exception:
        db.rollback()
        raise

    period = f"{work_date.year:04d}-{work_date.month:02d}"
    rebuild_timesheets(db, period, recalc_days=False, employee_ids=affected_ids)
    write_audit(
        db,
        actor=user,
        action="attendance.day.bulk",
        entity_type="attendance_day",
        entity_id=work_date.isoformat(),
        summary=f"{action} hàng loạt {len(affected)} NV ngày {work_date.isoformat()}",
        meta={
            "action": action,
            "work_date": work_date.isoformat(),
            "employee_codes": affected[:50],
            "skipped": skipped,
        },
    )
    return {
        "preview": False,
        "affected_count": len(affected),
        "skipped": skipped,
        "message": f"Đã cập nhật {len(affected)} dòng công ngày {work_date.isoformat()}.",
    }
