from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InsurancePeriodSummary(BaseModel):
    period: str
    employee_count: int
    total_bhxh: Decimal
    total_bhyt: Decimal
    total_bhtn: Decimal
    total_union_fee: Decimal
    total_pit: Decimal
    total_gross: Decimal
    total_net: Decimal
    pit_enabled_in_snapshot: bool | None = None


class InsuranceRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_code: str
    full_name: str
    si_enrolled: bool
    pit_enrolled: bool
    tax_dependent_count: int
    gross: Decimal
    bhxh: Decimal
    bhyt: Decimal
    bhtn: Decimal
    union_fee: Decimal
    pit_amount: Decimal
    net: Decimal


class InsuranceDeclarationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_code: str
    full_name: str
    si_book_no: str | None = None
    declaration_type: str
    declaration_type_label: str
    effective_month: str
    old_salary: Decimal
    new_salary: Decimal
    reason_code: str | None = None
    batch_no: str | None = None
    submitted_at: datetime | None = None
    status: str
    created_at: datetime | None = None


class InsuranceDeclarationProposeOut(BaseModel):
    effective_month: str
    created_count: int
    by_type: dict[str, int]
    items: list[InsuranceDeclarationOut]


class InsuranceDeclarationBatchExportOut(BaseModel):
    batch_no: str
    effective_month: str
    row_count: int
    filename: str
    content: str


class InsuranceDeclarationSubmitBody(BaseModel):
    effective_month: str | None = None
    batch_no: str | None = None
    declaration_ids: list[UUID] | None = None


class InsuranceDeclarationSubmitOut(BaseModel):
    marked: int
    batch_no: str | None = None
    message: str
