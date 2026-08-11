"""Schemas payroll."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PayrollRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pay_period_id: UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    employee_count: int
    message: str
    policy_snapshot_id: UUID | None


class PeriodOut(BaseModel):
    id: UUID
    period: str
    year: int
    month: int
    date_from: date
    date_to: date
    official_work_days: Decimal
    salary_divisor: Decimal
    status: str


class PeriodActionResult(BaseModel):
    period: PeriodOut
    affected_payslips: int
    message: str


class PayslipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pay_period_id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    pay_channel: str | None = None
    policy_snapshot_id: UUID | None
    wd_salary: Decimal
    allowance_total: Decimal
    ot_pay: Decimal
    other_adjustments: Decimal
    gross: Decimal
    taxable_income: Decimal
    bhxh: Decimal
    bhyt: Decimal
    bhtn: Decimal
    union_fee: Decimal
    other_deductions: Decimal
    pit_amount: Decimal
    net: Decimal
    status: str
    confirmed_at: datetime | None = None
    confirm_deadline: date | None = None
    lines: dict | None
    worked_days: Decimal | None = None
    al_days: Decimal | None = None
    rem_days: Decimal | None = None
    salary_divisor: Decimal | None = None
    period: str | None = None
    prev_net: Decimal | None = None
    net_delta: Decimal | None = None


class HRPayslipDetailOut(BaseModel):
    payslip: PayslipOut
    period: str
    work_lines: list[PayslipComponentOut]
    allowance_lines: list[PayslipComponentOut]
    deduction_lines: list[PayslipComponentOut]
    annual_leave_remaining: Decimal | None = None


class PayslipComponentOut(BaseModel):
    id: UUID
    payslip_id: UUID
    component_code: str
    component_name: str
    segment: str
    seq_no: int
    quantity: Decimal | None = None
    unit: str | None = None
    unit_amount: Decimal | None = None
    amount: Decimal
    note: str | None = None
    sort_order: int
    kind: str


class CalculateResult(BaseModel):
    run: PayrollRunOut
    payslips: list[PayslipOut]
    message: str


class EmployeeBonusCreate(BaseModel):
    employee_code: str
    bonus_year: int
    seq_times: int = 1
    bonus_code: str = "TET"
    bonus_amount: Decimal
    base_salary: Decimal | None = None
    bonus_rate: Decimal | None = None
    period: str
    reason: str = ""


class EmployeeBonusOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_code: str | None = None
    full_name: str | None = None
    bonus_year: int
    seq_times: int
    bonus_code: str
    base_salary: Decimal
    bonus_rate: Decimal
    bonus_amount: Decimal
    pay_period_id: UUID
    applied_at: datetime | None = None
    reason: str


class PolicyOptionOut(BaseModel):
    id: UUID
    name: str
    effective_from: date
    is_active: bool


class PayslipAmountsOut(BaseModel):
    wd_salary: Decimal
    allowance_total: Decimal
    ot_pay: Decimal
    gross: Decimal
    pit_amount: Decimal
    net: Decimal
    bonus_total: Decimal = Decimal("0")


class SimulateRequest(BaseModel):
    period: str
    policy_package_id: UUID | None = None
    scope: str = "all"
    department_id: UUID | None = None
    team_id: UUID | None = None
    employee_codes: list[str] | None = None


class SimulateRowOut(BaseModel):
    employee_id: UUID
    employee_code: str
    full_name: str
    current: PayslipAmountsOut | None
    simulated: PayslipAmountsOut
    delta_net: Decimal


class SimulateResult(BaseModel):
    period: str
    policy_package_id: UUID | None
    policy_package_name: str
    employee_count: int
    rows: list[SimulateRowOut]
    message: str
