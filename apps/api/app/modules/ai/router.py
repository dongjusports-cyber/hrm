"""API AI — Lớp A alerts + Lớp B query (file 08)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.deps import AdminUser, CurrentUser, DbSession, require_permission
from app.modules.ai import query as query_svc
from app.modules.ai import service
from app.modules.ai import settings_svc
from app.modules.ai import todos as todos_svc
from app.modules.ai import inbox as inbox_svc
from app.modules.ai.schemas import (
    AiAlertCreate,
    AiAlertOut,
    AiAlertsMineOut,
    AiInboxOut,
    AiQueryRequest,
    AiQueryResponse,
    AiSettingsOut,
    AiSettingsUpdate,
    TodosOut,
)
from app.modules.core.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/alerts/mine", response_model=AiAlertsMineOut)
def alerts_mine(
    user: CurrentUser,
    db: DbSession,
    unread_only: Annotated[bool, Query()] = False,
) -> AiAlertsMineOut:
    return service.list_mine(db, user, unread_only=unread_only)


@router.get("/todos", response_model=TodosOut)
def todos_mine(user: CurrentUser, db: DbSession) -> TodosOut:
    """Thẻ việc cần làm theo vai trò (5.7)."""
    return todos_svc.compute_todo_cards(db, user)


@router.get("/inbox", response_model=AiInboxOut)
def ai_inbox(
    user: CurrentUser,
    db: DbSession,
    light: Annotated[bool, Query()] = False,
) -> AiInboxOut:
    """Một GET: badge (light) hoặc việc cần làm + gợi ý hỏi (đầy đủ)."""
    return inbox_svc.build_inbox(db, user, light=light, evaluate=not light)


@router.post("/alerts/{alert_id}/read", response_model=AiAlertOut)
def alert_mark_read(alert_id: UUID, user: CurrentUser, db: DbSession) -> AiAlertOut:
    return service.mark_read(db, user, alert_id)


@router.post("/alerts/read-all")
def alerts_read_all(user: CurrentUser, db: DbSession) -> dict:
    return service.mark_all_read(db, user)


@router.post("/alerts", response_model=AiAlertOut | None)
def alerts_create_internal(
    body: AiAlertCreate,
    _admin: AdminUser,
    db: DbSession,
) -> AiAlertOut | None:
    """Tạo alert thủ công (Admin) — chủ yếu phục vụ test / vận hành."""
    return service.create_alert(db, body)


@router.post("/query", response_model=AiQueryResponse)
def ai_query(
    body: AiQueryRequest,
    db: DbSession,
    user: Annotated[User, Depends(require_permission("ai_query"))],
) -> AiQueryResponse:
    """Lớp B — Gemini on-demand. Chỉ user có ai_query; không trên Worker."""
    return query_svc.run_ai_query(db, user, body)


@router.post("/assist", response_model=AiQueryResponse)
def ai_assist(
    body: AiQueryRequest,
    db: DbSession,
    user: CurrentUser,
) -> AiQueryResponse:
    """HR tra cứu CSDL (không Gemini). Câu phân tích / chat tự do cần `ai_query`."""
    return query_svc.run_ai_query(db, user, body, direct_only=True)


@router.get("/settings", response_model=AiSettingsOut)
def ai_settings_get(_admin: AdminUser, db: DbSession) -> AiSettingsOut:
    return settings_svc.get_settings_out(db)


@router.put("/settings", response_model=AiSettingsOut)
def ai_settings_put(
    body: AiSettingsUpdate, _admin: AdminUser, db: DbSession
) -> AiSettingsOut:
    return settings_svc.update_settings(db, body)
