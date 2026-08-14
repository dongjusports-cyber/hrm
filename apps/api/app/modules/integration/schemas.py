"""Schemas Mitapro ingest."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PunchIn(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40, description="MSNV = MaNhanVien")
    punch_time: datetime
    ma_cham_cong: str | None = None
    device_id: str | None = None
    direction: Literal["IN", "OUT"] | None = None
    raw: dict[str, Any] | None = None


class MitaproPushRequest(BaseModel):
    punches: list[PunchIn] = Field(default_factory=list)
    synced_from: datetime | None = None
    synced_to: datetime | None = None
    agent_name: str | None = None
    claimed_job_id: UUID | None = Field(
        default=None,
        description="Job HR đã claim — ingest cập nhật cùng job (tránh poll lệch ID).",
    )
    chunk_final: bool = Field(
        default=True,
        description="False = còn chunk tiếp theo; API giữ job running, chưa tính lại công.",
    )


class MitaproErrorReport(BaseModel):
    """Agent báo sync thất bại (P2.5 → AI alert Admin)."""

    message: str = Field(min_length=1, max_length=2000)
    agent_name: str | None = None


class SyncJobOut(BaseModel):
    id: UUID
    started_at: datetime | None
    finished_at: datetime | None
    status: str
    records_in: int
    records_inserted: int
    records_skipped: int
    message: str
    source: str
    trigger: str
    sync_date_from: date | None = None
    sync_date_to: date | None = None

    model_config = {"from_attributes": True}


class SyncJobsListOut(BaseModel):
    total: int
    items: list[SyncJobOut]


class SyncRangeRequest(BaseModel):
    date_from: date = Field(..., alias="from")
    date_to: date = Field(..., alias="to")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def check_range(self) -> "SyncRangeRequest":
        if self.date_to < self.date_from:
            raise ValueError("date_to phải >= date_from")
        if (self.date_to - self.date_from).days > 92:
            raise ValueError("Khoảng ngày tối đa 92 ngày")
        return self


class MitaproPushResult(BaseModel):
    job: SyncJobOut
    detail: str


class IntegrationStatusOut(BaseModel):
    agent_configured: bool
    last_job: SyncJobOut | None
    last_success_at: datetime | None
    punch_count: int
    punch_unlinked_count: int = 0
    last_punch_at: datetime | None = None
    stale_threshold_hours: int = 24
    hours_since_data: float | None = None
    stale_warning: bool = False
    detail: str


class PunchOut(BaseModel):
    id: int
    employee_code: str
    employee_id: UUID | None
    punch_time: datetime
    direction: str | None
    sync_job_id: UUID | None
    source: str
    ma_cham_cong: str | None
    device_id: str | None

    model_config = {"from_attributes": True}


class UnlinkedPunchesOut(BaseModel):
    total: int
    items: list[PunchOut]
