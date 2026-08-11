"""Schemas AI alerts + query (Lớp A/B)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AiAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_key: str
    title: str
    body: str
    target_module: str
    is_read: bool
    user_id: UUID | None
    source_ref: str | None = None
    created_at: datetime | None


class AiAlertCreate(BaseModel):
    """Internal / hệ thống tạo alert."""

    rule_key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    body: str = ""
    target_module: str = "timekeeping"
    user_id: UUID | None = None
    source_ref: str | None = None


class AiAlertsMineOut(BaseModel):
    unread_count: int
    alerts: list[AiAlertOut]


class AiQueryRequest(BaseModel):
    message: str = Field(default="", max_length=4000)
    dispute_id: UUID | None = None


class AiQueryResponse(BaseModel):
    answer: str
    kind: str
    job_id: UUID
    dispute_id: UUID | None = None
    dispute_code: str | None = None
    model_name: str
    tokens_in: int
    tokens_out: int
    stub: bool
    remaining_today: int
    message: str


class AiSettingsOut(BaseModel):
    enabled: bool
    model_name: str
    max_queries_per_day: int
    max_output_tokens: int
    has_api_key: bool
    api_key_masked: str | None = None
    source: str  # database | env | none


class AiSettingsUpdate(BaseModel):
    enabled: bool | None = None
    model_name: str | None = Field(default=None, max_length=80)
    max_queries_per_day: int | None = None
    max_output_tokens: int | None = None
    api_key: str | None = Field(default=None, max_length=512)
    clear_api_key: bool = False


class TodoCardOut(BaseModel):
    key: str
    title: str
    body: str
    count: int
    target_module: str
    href: str
    priority: int = 100


class TodosOut(BaseModel):
    cards: list[TodoCardOut]
    total: int
