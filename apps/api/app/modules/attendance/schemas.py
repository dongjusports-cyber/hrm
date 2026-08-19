"""Schemas attendance days + timesheet."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttendanceDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    work_date: date
    first_in: datetime | None
    last_out: datetime | None
    worked_hours: Decimal
    late_minutes: int
    early_minutes: int
    ot_minutes: int
    ot_on_books_minutes: int = 0
    ot_external_minutes: int = 0
    ot_type: str | None
    punch_count: int
    is_workday: bool
    work_shift_id: str | None = None
    leave_code: str | None = None
    source: str = "machine"
    night_hours: Decimal = Decimal("0")
    sunday_hours: Decimal = Decimal("0")
    holiday_hours: Decimal = Decimal("0")
    ot_night_hours: Decimal = Decimal("0")
    segment: str = "official"
    is_locked: bool = False
    note: str = ""
    cycle_leave: bool = False
    edited_by_user_id: UUID | None = None
    edited_at: datetime | None = None


class CycleLeavePatch(BaseModel):
    employee_code: str
    work_date: date
    cycle_leave: bool


class CycleLeaveRowOut(BaseModel):
    employee_code: str
    full_name: str
    work_date: date
    first_in: datetime | None
    last_out: datetime | None
    worked_hours: Decimal
    note: str = ""


class RecalculateRequest(BaseModel):
    date_from: date = Field(..., alias="from")
    date_to: date = Field(..., alias="to")
    employee_code: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class RecalculateResult(BaseModel):
    days_upserted: int
    employees_touched: int
    skipped_unknown_codes: list[str]
    message: str


class LeaveTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    paid_by_company: bool
    counts_as_unauthorized: bool
    pay_ratio_percent: int | None = None
    paid_by_si: bool = False
    affects_attendance_bonus: bool = False
    counts_as_worked_day: bool = False
    requires_document: bool = False
    max_days_per_year: int | None = None


class PayPeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    year: int
    month: int
    date_from: date
    date_to: date
    official_work_days: Decimal
    salary_divisor: Decimal
    status: str


class TimesheetMonthOut(BaseModel):
    id: UUID
    pay_period_id: UUID
    period: str
    employee_id: UUID
    employee_code: str
    full_name: str
    worked_days: Decimal
    al_days: Decimal
    rem_days: Decimal
    late_count: int
    early_count: int
    ot_hours_weekday: Decimal
    ot_hours_external: Decimal = Decimal("0")
    ot_hours_weekend: Decimal
    ot_hours_holiday: Decimal
    ot_hours_by_rate: dict = {}


class TimesheetMonthDetailOut(BaseModel):
    id: UUID
    timesheet_month_id: UUID
    period: str
    employee_id: UUID
    employee_code: str
    full_name: str
    category: str
    segment: str
    hours: Decimal
    days: Decimal


class RebuildTimesheetResult(BaseModel):
    period: str
    pay_period_id: UUID
    rows_upserted: int
    message: str


class AdjustmentCreate(BaseModel):
    period: str
    employee_code: str
    kind: str  # leave | ot
    leave_code: str | None = None
    days: Decimal | None = None
    ot_type: str | None = "weekday"
    ot_hours: Decimal | None = None
    note: str = ""


class WorkShiftOut(BaseModel):
    """Ca làm việc (21§21.5, hạng mục 2.4)."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    start_time: time
    end_time: time
    lunch_start: time | None = None
    lunch_end: time | None = None
    dinner_start: time | None = None
    dinner_end: time | None = None
    ot_start: time | None = None
    night_start: time | None = None
    lunch_deduct_hours: Decimal
    dinner_deduct_hours: Decimal
    standard_hours: Decimal
    is_active: bool


class TeamShiftScheduleCreate(BaseModel):
    team_id: UUID
    work_date: date
    work_shift_id: str = Field(min_length=1, max_length=20)
    note: str = ""


class TeamShiftScheduleOut(BaseModel):
    id: UUID
    team_id: UUID
    team_code: str
    work_date: date
    work_shift_id: str
    note: str


class TeamEffectiveShiftOut(BaseModel):
    """Ca thật áp dụng cho một Tổ tại một ngày — override (team_shift_schedules) nếu có,
    không thì rơi về default_shift_id của Tổ."""

    team_id: UUID
    team_code: str
    work_date: date
    work_shift_id: str | None
    source: str  # override | team_default | none


class AdjustmentOut(BaseModel):
    id: UUID
    period: str
    employee_id: UUID
    employee_code: str
    full_name: str
    kind: str
    leave_code: str | None
    days: Decimal | None
    ot_type: str | None
    ot_hours: Decimal | None
    note: str
    created_by: str
    created_at: datetime | None


class AttendanceDayGridOut(AttendanceDayOut):
    id: UUID | None = None
    team_code: str | None = None
    team_name: str | None = None
    department_code: str | None = None
    department_name: str | None = None
    needs_action: bool = False
    row_flag: str = "ok"


class DayCellPatch(BaseModel):
    employee_code: str
    work_date: date
    first_in: datetime | None = None
    last_out: datetime | None = None
    leave_code: str | None = None
    note: str | None = None
    clear_note: bool = False
    clear_times: bool = False
    clear_first_in: bool = False
    clear_last_out: bool = False


class DayBulkPatchRequest(BaseModel):
    work_date: date
    employee_codes: list[str] = Field(min_length=1)
    action: str  # set_leave | set_times | clear_note
    leave_code: str | None = None
    first_in_time: time | None = None
    last_out_time: time | None = None
    note: str | None = None
    preview: bool = False


class DayBulkPatchResult(BaseModel):
    preview: bool
    affected_count: int
    skipped: list[dict]
    message: str


class LeaveRequestCreate(BaseModel):
    leave_type_code: str
    from_date: date
    to_date: date
    from_half: bool = False
    to_half: bool = False
    reason: str = ""
    submit: bool = True


class LeaveRequestOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    team_code: str | None = None
    department_code: str | None = None
    leave_type_code: str
    leave_type_name: str
    from_date: date
    to_date: date
    from_half: bool
    to_half: bool
    total_days: Decimal
    reason: str
    status: str
    submitted_at: datetime | None = None
    decided_by_username: str | None = None
    decided_at: datetime | None = None
    decided_note: str = ""
    annual_leave_remaining: Decimal | None = None
    created_at: datetime | None = None


class LeaveBulkDecideRequest(BaseModel):
    request_ids: list[UUID] = Field(min_length=1)
    action: str  # approve | reject
    decided_note: str = ""


class LeaveBulkDecideResult(BaseModel):
    approved_count: int
    rejected_count: int
    skipped: list[dict]
    message: str
