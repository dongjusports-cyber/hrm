"""API Hộp đen — Admin only (Cấu Hình → Log)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession
from app.modules.audit import service
from app.modules.audit.schemas import BlackBoxOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/blackbox", response_model=BlackBoxOut)
def get_blackbox(
    _admin: AdminUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 80,
) -> BlackBoxOut:
    return service.black_box(db, limit=limit)
