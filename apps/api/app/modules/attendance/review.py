"""
R3 / 10.8b — Rà soát công trước khóa kỳ: thiếu punch, punch lẻ.
HR sửa tay qua patch ngày (service.manual_set_day).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.modules.attendance.day_enrich import apply_calc_to_day_row, resolve_work_shift_id
from app.modules.attendance.engine import VN_TZ, calculate_day, is_company_workday, to_vn
from app.modules.attendance.models import AttendanceDay, PayPeriod
from app.modules.attendance.schemas import AttendanceDayOut
from app.modules.attendance.ot_split import load_ot_split_policy
from app.modules.attendance.service import _load_schedule, list_days
from app.modules.attendance.timesheet import _assert_open, ensure_pay_period, parse_period, rebuild_timesheets
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.mdm.models import Employee


class ReviewIssue(BaseModel):
    issue_type: str  # missing_punch | odd_punch | no_data
    severity: str  # warn
    employee_id: UUID
    employee_code: str
    full_name: str
    work_date: date | None = None
    day_id: UUID | None = None
    punch_count: int = 0
    message: str


class ReviewSummary(BaseModel):
    period: str
    date_from: date
    date_to: date
    period_status: str
    issue_count: int
    missing_punch: int
    odd_punch: int
    no_data: int
    issues: list[ReviewIssue]
    note: str = (
        "Rà soát trước khi khóa kỳ (R3). HR sửa tay giờ vào/ra hoặc nhập nghỉ/OT."
    )


class ManualDayPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_code: str
    work_date: date
    first_in: datetime | None = None
    last_out: datetime | None = None
    note: str = ""


def build_review(db: Session, period: str) -> ReviewSummary:
    year, month = parse_period(period)
    pay = (
        db.query(PayPeriod)
        .filter(PayPeriod.year == year, PayPeriod.month == month)
        .one_or_none()
    )
    if pay is None:
        pay = ensure_pay_period(db, period)

    schedule = _load_schedule(db)
    date_from = pay.date_from
    date_to = pay.date_to

    employees = {
        e.id: e
        for e in db.query(Employee)
        .filter(Employee.deleted_at.is_(None), Employee.status.in_(["active", "probation"]))
        .all()
    }
    if employees:
        days = (
            db.query(AttendanceDay)
            .filter(
                AttendanceDay.work_date >= date_from,
                AttendanceDay.work_date <= date_to,
                AttendanceDay.employee_id.in_(list(employees.keys())),
            )
            .all()
        )
    else:
        days = []
    day_map: dict[tuple[UUID, date], AttendanceDay] = {
        (d.employee_id, d.work_date): d for d in days
    }
    active_emps = {d.employee_id for d in days}

    issues: list[ReviewIssue] = []

    # NV active không có ngày công nào trong kỳ
    for emp in employees.values():
        if emp.id not in active_emps:
            issues.append(
                ReviewIssue(
                    issue_type="no_data",
                    severity="warn",
                    employee_id=emp.id,
                    employee_code=emp.employee_code,
                    full_name=emp.full_name,
                    message="Không có dữ liệu chấm công trong kỳ — kiểm tra Agent / map MSNV.",
                )
            )

    # NV đã có hoạt động: thiếu / lẻ punch trên ngày làm việc
    cur = date_from
    workdays: list[date] = []
    while cur <= date_to:
        if is_company_workday(cur, schedule):
            workdays.append(cur)
        cur += timedelta(days=1)

    for emp_id in active_emps:
        emp = employees.get(emp_id)
        if emp is None:
            continue
        for wd in workdays:
            row = day_map.get((emp_id, wd))
            if row is None or row.punch_count == 0:
                issues.append(
                    ReviewIssue(
                        issue_type="missing_punch",
                        severity="warn",
                        employee_id=emp.id,
                        employee_code=emp.employee_code,
                        full_name=emp.full_name,
                        work_date=wd,
                        day_id=row.id if row else None,
                        punch_count=row.punch_count if row else 0,
                        message=f"Thiếu punch ngày {wd.isoformat()} (ngày làm việc).",
                    )
                )
            elif row.punch_count == 1:
                issues.append(
                    ReviewIssue(
                        issue_type="odd_punch",
                        severity="warn",
                        employee_id=emp.id,
                        employee_code=emp.employee_code,
                        full_name=emp.full_name,
                        work_date=wd,
                        day_id=row.id,
                        punch_count=1,
                        message=(
                            f"Chấm lẻ ngày {wd.isoformat()} — "
                            f"{'chỉ có giờ vào' if row.first_in and not row.last_out else 'chỉ có giờ ra' if row.last_out and not row.first_in else 'thiếu vào hoặc ra'}."
                        ),
                    )
                )

    # Giới hạn trả về UI (500 NV × ~26 ngày có thể lớn)
    issues.sort(
        key=lambda i: (
            0 if i.issue_type == "missing_punch" else 1 if i.issue_type == "odd_punch" else 2,
            i.employee_code,
            i.work_date.isoformat() if i.work_date else "",
        )
    )
    missing = sum(1 for i in issues if i.issue_type == "missing_punch")
    odd = sum(1 for i in issues if i.issue_type == "odd_punch")
    no_data = sum(1 for i in issues if i.issue_type == "no_data")

    return ReviewSummary(
        period=period,
        date_from=date_from,
        date_to=date_to,
        period_status=pay.status,
        issue_count=len(issues),
        missing_punch=missing,
        odd_punch=odd,
        no_data=no_data,
        issues=issues[:500],
    )


def count_blocking_issues(db: Session, period: str) -> int:
    """Số cảnh báo thiếu/lẻ punch (không gồm no_data hàng loạt)."""
    rev = build_review(db, period)
    return rev.missing_punch + rev.odd_punch


def manual_set_day(db: Session, body: ManualDayPatch, user: User) -> AttendanceDayOut:
    """HR ghi giờ vào/ra tay → tính lại late/early/OT ngày đó."""
    pay = ensure_pay_period(db, f"{body.work_date.year:04d}-{body.work_date.month:02d}")
    _assert_open(pay)

    emp = (
        db.query(Employee)
        .filter(
            Employee.employee_code == body.employee_code.strip(),
            Employee.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI: không tìm thấy MSNV {body.employee_code}.",
        )
    if body.first_in is None or body.last_out is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: sửa tay cần đủ giờ vào và giờ ra (không tự bịa mốc còn lại).",
        )

    row = (
        db.query(AttendanceDay)
        .filter(
            AttendanceDay.employee_id == emp.id,
            AttendanceDay.work_date == body.work_date,
        )
        .one_or_none()
    )
    if row is None:
        row = AttendanceDay(employee_id=emp.id, work_date=body.work_date)
        db.add(row)
    if row.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: ngày công đã khóa — không sửa.",
        )

    schedule = _load_schedule(db)
    punches = [to_vn(body.first_in), to_vn(body.last_out)]
    calc = calculate_day(punches, body.work_date, schedule, ot_split=load_ot_split_policy(db))
    shift_id = resolve_work_shift_id(db, emp, body.work_date)
    apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=shift_id)
    row.source = "manual"
    row.note = (body.note or "").strip()
    row.edited_by_user_id = user.id
    row.edited_at = datetime.now(tz=VN_TZ)
    db.commit()
    db.refresh(row)

    period = f"{pay.year:04d}-{pay.month:02d}"
    rebuild_timesheets(db, period, recalc_days=False)
    write_audit(
        db,
        actor=user,
        action="attendance.day.manual",
        entity_type="attendance_day",
        entity_id=str(row.id),
        summary=(
            f"Sửa tay công {emp.employee_code} ngày {body.work_date.isoformat()}"
            + (f" — {body.note}" if body.note else "")
        ),
        meta={
            "employee_code": emp.employee_code,
            "work_date": body.work_date.isoformat(),
            "punch_count": row.punch_count,
            "note": (body.note or "")[:200],
        },
    )

    listed = list_days(db, body.work_date, body.work_date, emp.employee_code)
    if listed:
        return listed[0]
    return AttendanceDayOut(
        id=row.id,
        employee_id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        work_date=row.work_date,
        first_in=row.first_in,
        last_out=row.last_out,
        worked_hours=row.worked_hours,
        late_minutes=row.late_minutes,
        early_minutes=row.early_minutes,
        ot_minutes=row.ot_minutes,
        ot_on_books_minutes=row.ot_on_books_minutes,
        ot_external_minutes=row.ot_external_minutes,
        ot_type=row.ot_type,
        punch_count=row.punch_count,
        is_workday=row.is_workday,
    )
