"""Schemas dispute."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DisputeCreateRequest(BaseModel):
    reason_code: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=3, max_length=2000)


class DisputeAssignRequest(BaseModel):
    """Gán người xử lý — bỏ trống = gán cho chính mình."""

    user_id: UUID | None = None


class DisputeCloseRequest(BaseModel):
    note: str = Field(default="", max_length=2000, description="Ghi chú HR (tuỳ chọn)")


class DisputeOut(BaseModel):
    id: UUID
    code: str
    payslip_id: UUID
    employee_id: UUID
    employee_code: str
    employee_name: str
    period: str
    reason_code: str
    reason_label: str
    description: str
    status: str
    payslip_status: str
    assigned_user_id: UUID | None = None
    assigned_user_name: str | None = None
    created_at: datetime | None = None
    closed_at: datetime | None = None
    hr_note: str | None = None
    ai_summary: str | None = None


class DisputeReasonOut(BaseModel):
    code: str
    label: str
