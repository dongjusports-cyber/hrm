"""Schemas policy package."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyPackageOut(BaseModel):
    id: UUID
    name: str
    effective_from: date
    effective_to: date | None
    is_active: bool
    version: int
    payload: dict[str, Any]

    model_config = {"from_attributes": True}


class PolicyPackageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool | None = None
    payload: dict[str, Any]


class PolicyConfirmPreview(BaseModel):
    step: int
    status: str  # need_confirm | saved
    detail: str
    changed_money_fields: list[str]
    package: PolicyPackageOut | None = None


class InsuranceRateOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    effective_from: date
    effective_to: date | None
    si_employee_pct: Any
    hi_employee_pct: Any
    ui_employee_pct: Any
    union_pct: Any  # thực tế là số tiền cố định 44100đ (lệch tên cột 21)
    si_base_cap: Any
    region_min_wage: Any


class PitBracketOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    effective_from: date
    effective_to: date | None
    seq: int
    from_amount: Any
    rate_percent: Any


class PitDeductionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    effective_from: date
    effective_to: date | None
    self_amount: Any
    dependent_amount: Any


class SeniorityAllowanceTierOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    effective_from: date
    effective_to: date | None
    months_from: int
    months_to: int | None
    amount: Any


class AttendanceBonusRuleOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    effective_from: date
    effective_to: date | None
    late_count_half: int
    early_count_half: int
    late_count_zero: int
    early_count_zero: int
    exempt_leave_codes: list[str]
    full_amount: Any


class SeniorityAmountOut(BaseModel):
    months: int
    as_of: date
    amount: Any
    months_from: int
    months_to: int | None

