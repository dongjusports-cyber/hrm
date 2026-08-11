"""Schemas hộp đen."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str | None
    summary: str
    meta_json: dict[str, Any] | None = None
    ip: str | None = None
    created_at: datetime | None = None


class AuditExportOut(BaseModel):
    id: UUID
    user_id: UUID
    username: str | None
    full_name: str | None
    kind: str
    period: str | None
    row_count: int
    filename: str
    created_at: datetime | None = None


class AuditPolicyConfirmOut(BaseModel):
    id: UUID
    package_id: UUID
    actor_user_id: UUID
    actor_username: str | None
    confirm_step: int
    note: str
    created_at: datetime | None = None


class BlackBoxOut(BaseModel):
    actions: list[AuditLogOut]
    exports: list[AuditExportOut]
    policy_confirms: list[AuditPolicyConfirmOut]
    note: str
