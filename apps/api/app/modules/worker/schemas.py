"""Schemas Worker Portal."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.attendance.schemas import VnDateTime


class WorkerLoginRequest(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40, description="MSNV")
    password: str = Field(min_length=1, max_length=128)
    device_id: str = Field(min_length=8, max_length=64, description="Mã máy — khóa 1 MSNV / 1 điện thoại")


class WorkerChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class WorkerOut(BaseModel):
    id: UUID
    employee_code: str
    full_name: str
    must_change_password: bool
    employee_id: UUID | None
    department_code: str | None = None
    can_mobile_punch: bool = False
    punch_blocked_reason: str | None = None
    gps_required: bool = False


class WorkerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    worker: WorkerOut


class MessageOut(BaseModel):
    detail: str


class MoneyLine(BaseModel):
    label: str
    amount: Decimal


class PayslipLineOut(BaseModel):
    """Dòng phiếu worker — SL/ĐVT/TV khi có; thiếu → null (UI hiện —)."""

    label: str
    amount: Decimal | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    target: Decimal | None = None


class WorkerPayslipListOut(BaseModel):
    id: UUID
    period: str
    status: str
    net: Decimal
    gross: Decimal
    confirm_deadline: date | None = None


class WorkerPayslipDetailOut(BaseModel):
    id: UUID
    period: str
    status: str
    employee_code: str
    full_name: str
    department_name: str | None = None
    team_name: str | None = None
    position_title: str | None = None
    probation_salary: Decimal | None = None
    contract_salary: Decimal | None = None
    net: Decimal
    gross: Decimal
    taxable_income: Decimal
    wd_salary: Decimal
    allowance_total: Decimal
    ot_pay: Decimal
    other_adjustments: Decimal
    bhxh: Decimal
    bhyt: Decimal
    bhtn: Decimal
    union_fee: Decimal
    other_deductions: Decimal
    pit_amount: Decimal
    salary_divisor: Decimal | None = None
    worked_days: Decimal | None = None
    al_days: Decimal | None = None
    rem_days: Decimal | None = None
    work_subtotal: Decimal | None = None
    leave_subtotal: Decimal | None = None
    allowance_subtotal: Decimal | None = None
    deduction_subtotal: Decimal | None = None
    annual_leave_entitled: Decimal | None = None
    annual_leave_current: Decimal | None = None
    annual_leave_used: Decimal | None = None
    annual_leave_remaining: Decimal | None = None
    confirm_deadline: date | None = None
    confirmed_at: datetime | None = None
    work_lines: list[PayslipLineOut]
    leave_lines: list[PayslipLineOut]
    allowance_lines: list[PayslipLineOut]
    deduction_lines: list[PayslipLineOut]
    can_confirm: bool
    can_dispute: bool
    message: str


class WorkerLeaveBalanceOut(BaseModel):
    year: int
    days_per_year: Decimal
    accrued: Decimal
    used: Decimal
    pending_submitted: Decimal
    remaining: Decimal


class WorkerAttendanceDayOut(BaseModel):
    work_date: date
    first_in: VnDateTime | None = None
    last_out: VnDateTime | None = None
    worked_hours: Decimal = Decimal("0")
    late_minutes: int = 0
    early_minutes: int = 0
    ot_minutes: int = 0
    leave_code: str | None = None
    punch_count: int = 0
    is_workday: bool = True
    punches: list[VnDateTime] = Field(default_factory=list)


class WorkerAttendanceMonthOut(BaseModel):
    period: str
    date_from: date
    date_to: date
    worked_days: Decimal
    al_days: Decimal
    rem_days: Decimal
    late_count: int
    days: list[WorkerAttendanceDayOut]
