"""API Khiếu Nại — list + assign + close (P4.3/P4.4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.modules.core.models import User
from app.modules.dispute import service
from app.modules.dispute.schemas import (
    DisputeAssignRequest,
    DisputeCloseRequest,
    DisputeOut,
)

router = APIRouter(prefix="/disputes", tags=["dispute"])


def _require_dispute_viewer(user: CurrentUser) -> User:
    if not service.user_can_view_disputes(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền xem khiếu nại.",
        )
    return user


@router.get("", response_model=list[DisputeOut])
def list_disputes(
    db: DbSession,
    user: Annotated[User, Depends(_require_dispute_viewer)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[DisputeOut]:
    return service.list_disputes(db, user, status_filter=status_filter)


@router.get("/{dispute_id}", response_model=DisputeOut)
def get_dispute(
    dispute_id: UUID,
    db: DbSession,
    user: Annotated[User, Depends(_require_dispute_viewer)],
) -> DisputeOut:
    return service.get_dispute(db, user, dispute_id)


@router.post("/{dispute_id}/assign", response_model=DisputeOut)
def assign_dispute(
    dispute_id: UUID,
    body: DisputeAssignRequest,
    db: DbSession,
    user: Annotated[User, Depends(_require_dispute_viewer)],
) -> DisputeOut:
    return service.assign_dispute(db, user, dispute_id, body)


@router.post("/{dispute_id}/close", response_model=DisputeOut)
def close_dispute(
    dispute_id: UUID,
    body: DisputeCloseRequest,
    db: DbSession,
    user: Annotated[User, Depends(_require_dispute_viewer)],
) -> DisputeOut:
    return service.close_dispute(db, user, dispute_id, body)
