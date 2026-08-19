"""Rebuild attendance_days từ punches + lịch công ty."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.modules.attendance.day_enrich import (
    apply_calc_to_day_row,
    build_shift_cache,
    resolve_work_shift_id,
    wt_hours_early_on,
)
from app.modules.attendance.engine import VN_TZ, Schedule, calculate_day, to_vn
from app.modules.attendance.models import AttendanceDay, WorkShift
from app.modules.attendance.shift_schedule import engine_ot_kwargs, timing_from_shift
from app.modules.attendance.schemas import AttendanceDayOut, RecalculateResult
from app.modules.calendar.models import Holiday
from app.modules.calendar.service import get_work_week
from app.modules.integration.punch_resolver import is_patrol_guard_code
from app.modules.integration.models import AttendancePunch
from app.modules.mdm.models import Employee
from app.modules.policy.models import PolicyPackage
from app.modules.attendance.ot_split import load_ot_split_policy
from app.modules.policy.seed_payload import default_payload


def _punch_dedupe_window_seconds(db: Session) -> int:
    """Đọc work_time.punch_dedupe.window_seconds từ gói policy đang active."""
    fallback = int(default_payload()["work_time"]["punch_dedupe"]["window_seconds"])
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if not pkg or not isinstance(pkg.payload, dict):
        return fallback
    work_time = pkg.payload.get("work_time")
    if not isinstance(work_time, dict):
        return fallback
    dedupe = work_time.get("punch_dedupe")
    if not isinstance(dedupe, dict):
        return fallback
    try:
        return int(dedupe.get("window_seconds", fallback))
    except (TypeError, ValueError):
        return fallback


def _work_time_grace_seconds(db: Session) -> tuple[int, int]:
    """late_grace_seconds, early_grace_seconds từ policy (22§22.1 = 0)."""
    wt = default_payload()["work_time"]
    late = int(wt.get("late_grace_seconds", 0))
    early = int(wt.get("early_grace_seconds", 0))
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        policy_wt = pkg.payload.get("work_time")
        if isinstance(policy_wt, dict):
            try:
                late = int(policy_wt.get("late_grace_seconds", late))
                early = int(policy_wt.get("early_grace_seconds", early))
            except (TypeError, ValueError):
                pass
    return late, early


def _load_schedule(db: Session) -> Schedule:
    rule = get_work_week(db)
    holidays = {h.date for h in db.query(Holiday).all()}
    late_grace, early_grace = _work_time_grace_seconds(db)
    return Schedule(
        work_weekdays=list(rule.work_weekdays),
        morning_start=rule.morning_start,
        morning_end=rule.morning_end,
        afternoon_start=rule.afternoon_start,
        afternoon_end=rule.afternoon_end,
        grace_late_minutes=rule.grace_late_minutes,
        holiday_dates=holidays,
        grace_late_seconds=late_grace,
        grace_early_seconds=early_grace,
    )


def recalculate_days(
    db: Session,
    date_from: date,
    date_to: date,
    employee_code: str | None = None,
) -> RecalculateResult:
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: ngày kết thúc phải ≥ ngày bắt đầu.",
        )
    if (date_to - date_from).days > 92:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: khoảng tính công tối đa 92 ngày mỗi lần.",
        )

    schedule = _load_schedule(db)
    dedupe_window = _punch_dedupe_window_seconds(db)
    ot_split = load_ot_split_policy(db)
    # Lấy punch theo khoảng ±1 ngày để tránh lệch timezone biên
    start_dt = datetime(date_from.year, date_from.month, date_from.day, tzinfo=VN_TZ) - timedelta(days=1)
    end_dt = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=VN_TZ) + timedelta(days=1)

    q = db.query(AttendancePunch).filter(
        AttendancePunch.punch_time >= start_dt,
        AttendancePunch.punch_time <= end_dt,
        ~AttendancePunch.employee_code.like("200%"),
    )
    if employee_code:
        q = q.filter(AttendancePunch.employee_code == employee_code.strip())
    punches = q.all()

    emp_q = db.query(Employee).filter(Employee.deleted_at.is_(None))
    if employee_code:
        emp_q = emp_q.filter(Employee.employee_code == employee_code.strip())
    employees = {e.employee_code: e for e in emp_q.all()}

    grouped: dict[tuple[str, date], list[datetime]] = defaultdict(list)
    unknown: set[str] = set()
    for p in punches:
        vn = to_vn(p.punch_time)
        wd = vn.date()
        if wd < date_from or wd > date_to:
            continue
        code = p.employee_code.strip()
        if is_patrol_guard_code(code):
            continue
        if code not in employees:
            unknown.add(code)
            continue
        grouped[(code, wd)].append(p.punch_time)

    upserted = 0
    touched_emps: set[str] = set()
    emp_ids = [e.id for e in employees.values()]
    day_map: dict[tuple[UUID, date], AttendanceDay] = {}
    if emp_ids:
        for row in db.query(AttendanceDay).filter(
            AttendanceDay.work_date >= date_from,
            AttendanceDay.work_date <= date_to,
            AttendanceDay.employee_id.in_(emp_ids),
        ):
            day_map[(row.employee_id, row.work_date)] = row

    work_dates = {wd for _, wd in grouped.keys()}
    team_ids = {e.team_id for e in employees.values() if e.team_id is not None}
    shift_cache = build_shift_cache(db, team_ids, work_dates)

    from app.modules.attendance.seed_shifts import ADMIN_SHIFT_CODE

    # Ca ADMIN / CLEANER / COOKER — nạp 1 query, tránh N+1 trong vòng lặp.
    shift_map = {s.code: s for s in db.query(WorkShift).all()}

    from app.modules.mdm.service import active_wt_regime_hours_batch

    regime_map = active_wt_regime_hours_batch(db, emp_ids, date_from, date_to)

    for (code, wd), times in grouped.items():
        emp = employees[code]
        row = day_map.get((emp.id, wd))
        if row is not None and (row.is_locked or row.source == "manual"):
            continue
        if emp.team_id is None:
            shift_id = ADMIN_SHIFT_CODE
        else:
            shift_id = shift_cache.get((emp.team_id, wd), ADMIN_SHIFT_CODE)
        # Nối ca của Tổ vào engine (22§22.13): dùng lịch + mốc OT theo ca.
        timing = timing_from_shift(shift_map.get(shift_id), schedule)
        calc = calculate_day(
            times,
            wd,
            timing.schedule,
            punch_dedupe_window_seconds=dedupe_window,
            ot_split=ot_split,
            wt_hours_early=regime_map.get((emp.id, wd)),
            **engine_ot_kwargs(timing),
        )
        if row is None:
            row = AttendanceDay(employee_id=emp.id, work_date=wd)
            db.add(row)
            day_map[(emp.id, wd)] = row
        apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=shift_id)
        upserted += 1
        touched_emps.add(code)

    db.commit()
    skipped = sorted(unknown)
    msg = f"Đã tính lại {upserted} ngày công."
    if skipped:
        msg += f" Bỏ qua MSNV chưa có hồ sơ: {', '.join(skipped)}."
    return RecalculateResult(
        days_upserted=upserted,
        employees_touched=len(touched_emps),
        skipped_unknown_codes=skipped,
        message=msg,
    )


def reapply_wt_on_manual_days(
    db: Session,
    employee_code: str,
    date_from: date,
    date_to: date,
) -> int:
    """Tính lại ngày HR chấm tay khi gán/sửa chế độ về sớm.

    recalculate_days bỏ qua source=manual (tránh nuốt giờ tay). Gán thai sản /
    nuôi con sau khi đã sửa lưới vẫn phải cộng giờ về sớm vào công.
    """
    emp = (
        db.query(Employee)
        .filter(Employee.employee_code == employee_code.strip(), Employee.deleted_at.is_(None))
        .one_or_none()
    )
    if emp is None or date_to < date_from:
        return 0
    schedule = _load_schedule(db)
    ot_split = load_ot_split_policy(db)
    days = (
        db.query(AttendanceDay)
        .filter(
            AttendanceDay.employee_id == emp.id,
            AttendanceDay.work_date >= date_from,
            AttendanceDay.work_date <= date_to,
            AttendanceDay.is_locked.is_(False),
            AttendanceDay.source == "manual",
            AttendanceDay.first_in.isnot(None),
            AttendanceDay.last_out.isnot(None),
        )
        .all()
    )
    n = 0
    for row in days:
        shift_id = resolve_work_shift_id(db, emp, row.work_date)
        timing = timing_from_shift(db.get(WorkShift, shift_id), schedule)
        punches = [to_vn(row.first_in), to_vn(row.last_out)]
        src = row.source
        leave = row.leave_code
        calc = calculate_day(
            punches,
            row.work_date,
            timing.schedule,
            ot_split=ot_split,
            wt_hours_early=wt_hours_early_on(db, emp.id, row.work_date),
            **engine_ot_kwargs(timing),
        )
        apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=shift_id)
        row.source = src
        row.leave_code = leave
        n += 1
    if n:
        db.commit()
    return n


def list_days(
    db: Session,
    date_from: date,
    date_to: date,
    employee_code: str | None = None,
) -> list[AttendanceDayOut]:
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: ngày kết thúc phải ≥ ngày bắt đầu.",
        )
    q = (
        db.query(AttendanceDay, Employee)
        .join(Employee, Employee.id == AttendanceDay.employee_id)
        .filter(
            and_(
                AttendanceDay.work_date >= date_from,
                AttendanceDay.work_date <= date_to,
                Employee.deleted_at.is_(None),
            )
        )
        .order_by(AttendanceDay.work_date, Employee.employee_code)
    )
    if employee_code:
        q = q.filter(Employee.employee_code == employee_code.strip())
    rows = q.all()
    out: list[AttendanceDayOut] = []
    for day, emp in rows:
        out.append(
            AttendanceDayOut(
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
        )
    return out


def _months_covering(date_from: date, date_to: date) -> list[str]:
    out: list[str] = []
    y, m = date_from.year, date_from.month
    while (y, m) <= (date_to.year, date_to.month):
        out.append(f"{y:04d}-{m:02d}")
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def sync_maternity_mle_days(db: Session, employee_id: UUID, date_from: date, date_to: date) -> int:
    """Gán MLE các ngày trong chế độ Nghỉ thai sản; gỡ MLE khi đã cắt giai đoạn.

    Không đụng ngày khóa. Không xóa MLE nếu có đơn nghỉ thai sản đã duyệt.
    """
    from app.modules.attendance.models import LeaveRequest
    from app.modules.attendance.timesheet import rebuild_timesheets, seed_leave_types
    from app.modules.mdm.models import EmployeeWtRegime

    if date_to < date_from:
        return 0
    seed_leave_types(db)
    maternity_rows = (
        db.query(EmployeeWtRegime)
        .filter(
            EmployeeWtRegime.employee_id == employee_id,
            EmployeeWtRegime.regime_type == "MATERNITY",
            EmployeeWtRegime.date_from <= date_to,
            EmployeeWtRegime.date_to >= date_from,
        )
        .all()
    )
    maternity_dates: set[date] = set()
    for r in maternity_rows:
        cur = max(r.date_from, date_from)
        end = min(r.date_to, date_to)
        while cur <= end:
            maternity_dates.add(cur)
            cur += timedelta(days=1)

    approved = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_code.in_(("MLE", "MC")),
            LeaveRequest.status == "approved",
            LeaveRequest.from_date <= date_to,
            LeaveRequest.to_date >= date_from,
        )
        .all()
    )
    approved_dates: set[date] = set()
    for req in approved:
        cur = max(req.from_date, date_from)
        end = min(req.to_date, date_to)
        while cur <= end:
            approved_dates.add(cur)
            cur += timedelta(days=1)

    existing = {
        row.work_date: row
        for row in db.query(AttendanceDay).filter(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.work_date >= date_from,
            AttendanceDay.work_date <= date_to,
        )
    }
    changed = 0
    cursor = date_from
    while cursor <= date_to:
        row = existing.get(cursor)
        want_mle = cursor in maternity_dates
        keep_request = cursor in approved_dates
        if row is not None and row.is_locked:
            cursor += timedelta(days=1)
            continue
        if want_mle:
            if row is None:
                row = AttendanceDay(
                    employee_id=employee_id,
                    work_date=cursor,
                    source="import",
                    leave_code="MLE",
                    leave_days=Decimal("1"),
                )
                db.add(row)
                changed += 1
            elif row.leave_code != "MLE":
                row.leave_code = "MLE"
                row.leave_days = Decimal("1")
                if row.source != "manual":
                    row.source = "import"
                changed += 1
        elif row is not None and row.leave_code == "MLE" and not keep_request:
            row.leave_code = None
            row.leave_days = Decimal("0")
            changed += 1
        cursor += timedelta(days=1)

    if changed:
        db.flush()
        from fastapi import HTTPException as FastHTTPException

        for period in _months_covering(date_from, date_to):
            try:
                rebuild_timesheets(db, period, recalc_days=False, employee_id=employee_id)
            except FastHTTPException:
                pass
    return changed
