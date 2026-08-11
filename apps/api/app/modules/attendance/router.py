"""API attendance days + timesheet tháng (P2.3–P2.4)."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import DbSession, require_module
from app.modules.attendance import leave_requests as lr
from app.modules.attendance import review as review_mod
from app.modules.attendance.day_grid import bulk_patch_days, list_days_grid, patch_day_cell
from app.modules.attendance import service
from app.modules.attendance import timesheet as ts
from app.modules.attendance.review import ManualDayPatch, ReviewSummary
from app.modules.attendance.schemas import (
    AdjustmentCreate,
    AdjustmentOut,
    AttendanceDayGridOut,
    AttendanceDayOut,
    DayBulkPatchRequest,
    DayBulkPatchResult,
    DayCellPatch,
    LeaveBulkDecideRequest,
    LeaveBulkDecideResult,
    LeaveRequestCreate,
    LeaveRequestOut,
    LeaveTypeOut,
    PayPeriodOut,
    RebuildTimesheetResult,
    RecalculateRequest,
    RecalculateResult,
    TimesheetMonthDetailOut,
    TimesheetMonthOut,
)
from app.modules.core.models import User

router = APIRouter(tags=["attendance"])

TimekeepingUser = Annotated[User, Depends(require_module("timekeeping"))]


@router.post("/attendance/recalculate", response_model=RecalculateResult)
def attendance_recalculate(
    body: RecalculateRequest,
    _user: TimekeepingUser,
    db: DbSession,
) -> RecalculateResult:
    return service.recalculate_days(
        db,
        date_from=body.date_from,
        date_to=body.date_to,
        employee_code=body.employee_code,
    )


@router.get("/attendance/days", response_model=list[AttendanceDayOut])
def attendance_days(
    _user: TimekeepingUser,
    db: DbSession,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
    employee_code: str | None = None,
    anomalies_only: bool = False,
) -> list[AttendanceDayOut]:
    rows = service.list_days(db, date_from=date_from, date_to=date_to, employee_code=employee_code)
    if anomalies_only:
        rows = [r for r in rows if r.late_minutes > 0 or r.early_minutes > 0]
    return rows


@router.get("/attendance/leave-types", response_model=list[LeaveTypeOut])
def leave_types(_user: TimekeepingUser, db: DbSession) -> list[LeaveTypeOut]:
    return ts.list_leave_types(db)


@router.get("/attendance/pay-periods/{period}", response_model=PayPeriodOut)
def pay_period(period: str, _user: TimekeepingUser, db: DbSession) -> PayPeriodOut:
    return ts.get_pay_period_out(db, period)


@router.get("/attendance/timesheets", response_model=list[TimesheetMonthOut])
def timesheets(
    _user: TimekeepingUser,
    db: DbSession,
    period: Annotated[str, Query(description="YYYY-MM")],
) -> list[TimesheetMonthOut]:
    return ts.list_timesheets(db, period)


@router.get("/attendance/timesheets/details", response_model=list[TimesheetMonthDetailOut])
def timesheet_details(
    _user: TimekeepingUser,
    db: DbSession,
    period: Annotated[str, Query(description="YYYY-MM")],
    employee_code: str | None = None,
) -> list[TimesheetMonthDetailOut]:
    return ts.list_timesheet_details(db, period, employee_code=employee_code)


@router.post("/attendance/timesheets/rebuild", response_model=RebuildTimesheetResult)
def timesheets_rebuild(
    _user: TimekeepingUser,
    db: DbSession,
    period: Annotated[str, Query(description="YYYY-MM")],
) -> RebuildTimesheetResult:
    return ts.rebuild_timesheets(db, period, recalc_days=True)


@router.get("/attendance/adjustments", response_model=list[AdjustmentOut])
def adjustments_list(
    _user: TimekeepingUser,
    db: DbSession,
    period: Annotated[str, Query()],
    employee_code: str | None = None,
) -> list[AdjustmentOut]:
    return ts.list_adjustments(db, period, employee_code=employee_code)


@router.post("/attendance/adjustments", response_model=AdjustmentOut)
def adjustments_create(
    body: AdjustmentCreate,
    user: TimekeepingUser,
    db: DbSession,
) -> AdjustmentOut:
    return ts.create_adjustment(db, body, user)


@router.delete("/attendance/adjustments/{adjustment_id}")
def adjustments_delete(
    adjustment_id: UUID,
    user: TimekeepingUser,
    db: DbSession,
) -> dict:
    return ts.delete_adjustment(db, adjustment_id, user)


@router.get("/attendance/review", response_model=ReviewSummary)
def attendance_review(
    _user: TimekeepingUser,
    db: DbSession,
    period: Annotated[str, Query(description="YYYY-MM")],
) -> ReviewSummary:
    """R3 — rà soát thiếu/lẻ punch trước khi khóa kỳ."""
    return review_mod.build_review(db, period)


@router.patch("/attendance/days/manual", response_model=AttendanceDayOut)
def attendance_day_manual(
    body: ManualDayPatch,
    user: TimekeepingUser,
    db: DbSession,
) -> AttendanceDayOut:
    """HR sửa tay giờ vào/ra một ngày công."""
    return review_mod.manual_set_day(db, body, user)


@router.get("/attendance/leave-requests", response_model=list[LeaveRequestOut])
def leave_requests_list(
    _user: TimekeepingUser,
    db: DbSession,
    status: str | None = "submitted",
    employee_code: str | None = None,
) -> list[LeaveRequestOut]:
    from app.modules.mdm.models import Employee

    emp_id = None
    if employee_code:
        emp = (
            db.query(Employee)
            .filter(Employee.employee_code == employee_code.strip(), Employee.deleted_at.is_(None))
            .one_or_none()
        )
        if emp is None:
            raise HTTPException(status_code=404, detail=f"Trợ Lý AI: không tìm thấy MSNV {employee_code}.")
        emp_id = emp.id
    rows = lr.list_leave_requests(
        db, status=status, employee_id=emp_id, include_balance=True
    )
    return [LeaveRequestOut.model_validate(r) for r in rows]


@router.get("/attendance/days/grid", response_model=list[AttendanceDayGridOut])
def attendance_days_grid(
    _user: TimekeepingUser,
    db: DbSession,
    work_date: Annotated[date, Query(alias="date")],
    needs_action_only: bool = False,
) -> list[AttendanceDayGridOut]:
    return list_days_grid(db, work_date, needs_action_only=needs_action_only)


@router.patch("/attendance/days/cell", response_model=AttendanceDayOut)
def attendance_day_cell(
    body: DayCellPatch,
    user: TimekeepingUser,
    db: DbSession,
) -> AttendanceDayOut:
    return patch_day_cell(
        db,
        user,
        employee_code=body.employee_code,
        work_date=body.work_date,
        first_in=body.first_in,
        last_out=body.last_out,
        leave_code=body.leave_code,
        note=body.note,
        clear_note=body.clear_note,
    )


@router.post("/attendance/days/bulk", response_model=DayBulkPatchResult)
def attendance_days_bulk(
    body: DayBulkPatchRequest,
    user: TimekeepingUser,
    db: DbSession,
) -> DayBulkPatchResult:
    result = bulk_patch_days(
        db,
        user,
        work_date=body.work_date,
        employee_codes=body.employee_codes,
        action=body.action.strip().lower(),
        leave_code=body.leave_code,
        first_in_time=body.first_in_time,
        last_out_time=body.last_out_time,
        note=body.note,
        preview=body.preview,
    )
    return DayBulkPatchResult.model_validate(result)


@router.post("/attendance/leave-requests/bulk-decide", response_model=LeaveBulkDecideResult)
def leave_requests_bulk_decide(
    body: LeaveBulkDecideRequest,
    user: TimekeepingUser,
    db: DbSession,
) -> LeaveBulkDecideResult:
    result = lr.bulk_decide_leave_requests(
        db,
        request_ids=body.request_ids,
        action=body.action.strip().lower(),
        decided_note=body.decided_note,
        decider=user,
    )
    return LeaveBulkDecideResult.model_validate(result)
