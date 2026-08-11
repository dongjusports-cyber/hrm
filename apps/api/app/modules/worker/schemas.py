"""Schemas Worker Portal."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WorkerLoginRequest(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40, description="MSNV")
    password: str = Field(min_length=1, max_length=128)


class WorkerChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class WorkerOut(BaseModel):
    id: UUID
    employee_code: str
    full_name: str
    must_change_password: bool
    employee_id: UUID | None


class WorkerTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    worker: WorkerOut


class MessageOut(BaseModel):
    detail: str


class MoneyLine(BaseModel):
    label: str
    amount: Decimal


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
    net: Decimal
    gross: Decimal
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
    worked_days: Decimal | None = None
    al_days: Decimal | None = None
    rem_days: Decimal | None = None
    confirm_deadline: date | None = None
    confirmed_at: datetime | None = None
    income_lines: list[MoneyLine]
    deduction_lines: list[MoneyLine]
    can_confirm: bool
    can_dispute: bool
    message: str
