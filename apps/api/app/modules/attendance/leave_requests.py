"""Đơn xin nghỉ + duyệt hàng loạt (hạng mục 3.6, 21§21.5, 23§96)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.annual_leave_ledger import annual_leave_remaining, record_leave_use
from app.modules.attendance.models import AttendanceDay, LeaveRequest, LeaveType
from app.modules.attendance.timesheet import seed_leave_types
from app.modules.core.models import User
from app.modules.mdm.models import Department, Employee, Team

ACTIVE_STATUSES = ("draft", "submitted", "approved")
Q2 = Decimal("0.01")
VN = timezone(timedelta(hours=7))


def _now() -> datetime:
    return datetime.now(tz=VN)


def calc_total_days(
    from_date: date,
    to_date: date,
    *,
    from_half: bool = False,
    to_half: bool = False,
) -> Decimal:
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: ngày kết thúc nghỉ phải ≥ ngày bắt đầu.",
        )
    span = (to_date - from_date).days + 1
    total = Decimal(span)
    if from_half:
        total -= Decimal("0.5")
    if to_half:
        total -= Decimal("0.5")
    if total <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: số ngày nghỉ phải > 0.",
        )
    return total.quantize(Q2, rounding=ROUND_HALF_UP)


def _assert_no_overlap(
    db: Session,
    employee_id: UUID,
    from_date: date,
    to_date: date,
    *,
    exclude_id: UUID | None = None,
) -> None:
    q = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status.in_(ACTIVE_STATUSES),
        LeaveRequest.from_date <= to_date,
        LeaveRequest.to_date >= from_date,
    )
    if exclude_id:
        q = q.filter(LeaveRequest.id != exclude_id)
    if q.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: trùng khoảng ngày với đơn nghỉ đang hiệu lực.",
        )


def _leave_days_for_date(req: LeaveRequest, cur: date) -> Decimal:
    """1.0 cả ngày; 0.5 nếu ngày đầu from_half hoặc ngày cuối to_half (QA-04)."""
    days = Decimal("1")
    if cur == req.from_date and req.from_half:
        days -= Decimal("0.5")
    if cur == req.to_date and req.to_half:
        days -= Decimal("0.5")
    if days <= 0:
        days = Decimal("0.5")
    return days


def _months_covering(from_date: date, to_date: date) -> list[str]:
    out: list[str] = []
    y, m = from_date.year, from_date.month
    while (y, m) <= (to_date.year, to_date.month):
        out.append(f"{y:04d}-{m:02d}")
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def _apply_approved_leave(db: Session, req: LeaveRequest) -> None:
    """Gán leave_code + leave_days lên attendance_days (không đụng dòng is_locked)."""
    cur = req.from_date
    while cur <= req.to_date:
        row = (
            db.query(AttendanceDay)
            .filter(AttendanceDay.employee_id == req.employee_id, AttendanceDay.work_date == cur)
            .one_or_none()
        )
        if row is None:
            row = AttendanceDay(employee_id=req.employee_id, work_date=cur, source="import")
            db.add(row)
        if not row.is_locked:
            row.leave_code = req.leave_type_code
            row.leave_days = _leave_days_for_date(req, cur)
            row.source = "import"
        cur += timedelta(days=1)


def _row_out(
    db: Session,
    req: LeaveRequest,
    emp: Employee,
    lt: LeaveType | None,
    *,
    include_balance: bool = False,
) -> dict:
    team_code = None
    dept_code = None
    if emp.team_id:
        team = db.get(Team, emp.team_id)
        if team:
            team_code = team.code
            dept = db.get(Department, team.department_id)
            dept_code = dept.code if dept else None
    remaining = None
    if include_balance and req.leave_type_code == "ALE":
        remaining = annual_leave_remaining(db, emp.id, req.from_date)
    return {
        "id": req.id,
        "employee_id": emp.id,
        "employee_code": emp.employee_code,
        "full_name": emp.full_name,
        "team_code": team_code,
        "department_code": dept_code,
        "leave_type_code": req.leave_type_code,
        "leave_type_name": lt.name if lt else req.leave_type_code,
        "from_date": req.from_date,
        "to_date": req.to_date,
        "from_half": req.from_half,
        "to_half": req.to_half,
        "total_days": req.total_days,
        "reason": req.reason,
        "status": req.status,
        "submitted_at": req.submitted_at,
        "decided_by_username": None,
        "decided_at": req.decided_at,
        "decided_note": req.decided_note,
        "annual_leave_remaining": remaining,
        "created_at": req.created_at,
    }


def create_leave_request(
    db: Session,
    *,
    employee: Employee,
    leave_type_code: str,
    from_date: date,
    to_date: date,
    from_half: bool,
    to_half: bool,
    reason: str,
    submit: bool,
) -> dict:
    seed_leave_types(db)
    code = leave_type_code.strip().upper()
    lt = db.get(LeaveType, code)
    if lt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: mã nghỉ {leave_type_code} không có trong danh mục.",
        )
    total = calc_total_days(from_date, to_date, from_half=from_half, to_half=to_half)
    _assert_no_overlap(db, employee.id, from_date, to_date)
    row = LeaveRequest(
        employee_id=employee.id,
        leave_type_code=code,
        from_date=from_date,
        to_date=to_date,
        from_half=from_half,
        to_half=to_half,
        total_days=total,
        reason=(reason or "").strip(),
        status="submitted" if submit else "draft",
        submitted_at=_now() if submit else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_out(db, row, employee, lt)


def list_leave_requests(
    db: Session,
    *,
    status: str | None = None,
    employee_id: UUID | None = None,
    include_balance: bool = False,
) -> list[dict]:
    q = db.query(LeaveRequest, Employee).join(Employee, Employee.id == LeaveRequest.employee_id)
    q = q.filter(Employee.deleted_at.is_(None))
    if status:
        q = q.filter(LeaveRequest.status == status.strip().lower())
    if employee_id:
        q = q.filter(LeaveRequest.employee_id == employee_id)
    q = q.order_by(LeaveRequest.submitted_at.desc().nullslast(), LeaveRequest.created_at.desc())
    out: list[dict] = []
    for req, emp in q.all():
        lt = db.get(LeaveType, req.leave_type_code)
        out.append(_row_out(db, req, emp, lt, include_balance=include_balance))
    return out


def bulk_decide_leave_requests(
    db: Session,
    *,
    request_ids: list[UUID],
    action: str,
    decided_note: str,
    decider: User,
) -> dict:
    if action not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: action phải là approve hoặc reject.",
        )
    if not request_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: chọn ít nhất một đơn.",
        )
    rows = (
        db.query(LeaveRequest, Employee)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .filter(LeaveRequest.id.in_(request_ids))
        .all()
    )
    by_id = {r.id: (r, e) for r, e in rows}
    approved = 0
    rejected = 0
    skipped: list[dict] = []
    note = (decided_note or "").strip()
    now = _now()
    rebuild_periods: set[str] = set()

    for rid in request_ids:
        pair = by_id.get(rid)
        if pair is None:
            skipped.append({"id": str(rid), "employee_code": None, "reason": "Không tìm thấy đơn."})
            continue
        req, emp = pair
        if req.status != "submitted":
            skipped.append(
                {
                    "id": str(rid),
                    "employee_code": emp.employee_code,
                    "reason": f"Trạng thái {req.status} — không duyệt được.",
                }
            )
            continue
        if action == "approve" and req.leave_type_code == "ALE":
            remaining = annual_leave_remaining(db, emp.id, req.from_date)
            if req.total_days > remaining:
                skipped.append(
                    {
                        "id": str(rid),
                        "employee_code": emp.employee_code,
                        "reason": (
                            f"Vượt số dư phép (còn {remaining}, xin {req.total_days} ngày)."
                        ),
                    }
                )
                continue
        if action == "approve":
            req.status = "approved"
            _apply_approved_leave(db, req)
            if req.leave_type_code == "ALE":
                record_leave_use(
                    db,
                    employee_id=emp.id,
                    leave_request_id=req.id,
                    days=req.total_days,
                    entry_date=req.from_date,
                )
            rebuild_periods.update(_months_covering(req.from_date, req.to_date))
            approved += 1
        else:
            req.status = "rejected"
            rejected += 1
        req.decided_by_user_id = decider.id
        req.decided_at = now
        req.decided_note = note

    db.commit()
    # QA-10: cộng lại bảng công tháng sau khi duyệt phép (leave_code đã ghi lên ngày).
    if rebuild_periods:
        from app.modules.attendance.timesheet import rebuild_timesheets

        for period in sorted(rebuild_periods):
            try:
                rebuild_timesheets(db, period, recalc_days=False)
            except HTTPException:
                pass
    msg = f"Đã duyệt {approved}, từ chối {rejected} đơn."
    if skipped:
        msg += f" Bỏ qua {len(skipped)} đơn."
    from app.modules.audit.service import write_audit

    write_audit(
        db,
        actor=decider,
        action="leave_request.bulk_decide",
        entity_type="leave_request",
        entity_id=",".join(str(i) for i in request_ids[:5]),
        summary=msg,
        meta={"action": action, "approved": approved, "rejected": rejected, "skipped": len(skipped)},
    )
    return {
        "approved_count": approved,
        "rejected_count": rejected,
        "skipped": skipped,
        "message": msg,
    }
