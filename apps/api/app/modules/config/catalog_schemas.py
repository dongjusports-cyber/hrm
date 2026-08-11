"""Schemas Admin › Danh mục (2.8)."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeaveTypeAdminOut(BaseModel):
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


class LeaveTypeAdminCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    paid_by_company: bool = False
    counts_as_unauthorized: bool = False
    pay_ratio_percent: int | None = None
    paid_by_si: bool = False
    affects_attendance_bonus: bool = False
    counts_as_worked_day: bool = False
    requires_document: bool = False
    max_days_per_year: int | None = None


class LeaveTypeAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    paid_by_company: bool | None = None
    counts_as_unauthorized: bool | None = None
    pay_ratio_percent: int | None = None
    paid_by_si: bool | None = None
    affects_attendance_bonus: bool | None = None
    counts_as_worked_day: bool | None = None
    requires_document: bool | None = None
    max_days_per_year: int | None = None


class PayComponentAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    kind: str
    default_amount: Decimal
    proration: str
    proration_rule: str
    include_in_si_base: bool
    include_in_ot_base: bool
    affects_si_base: bool
    affects_ot_base: bool
    affects_pit: bool
    is_active: bool


class PayComponentAdminCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="earning", pattern="^(earning|deduction|info)$")
    default_amount: Decimal = Decimal("0")
    proration: str = "fixed"
    proration_rule: str = "none"
    include_in_si_base: bool = False
    include_in_ot_base: bool = False
    affects_si_base: bool = False
    affects_ot_base: bool = False
    affects_pit: bool = True


class PayComponentAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, pattern="^(earning|deduction|info)$")
    default_amount: Decimal | None = None
    proration: str | None = None
    proration_rule: str | None = None
    include_in_si_base: bool | None = None
    include_in_ot_base: bool | None = None
    affects_si_base: bool | None = None
    affects_ot_base: bool | None = None
    affects_pit: bool | None = None
    is_active: bool | None = None


class LookupValueAdminCreate(BaseModel):
    group_code: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    name_local: str | None = None
    sort_order: int = 0
    is_active: bool = True


class LookupValueAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    name_local: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
