"""Admin — ma trận vai trò × module (2.7)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import AdminUser, DbSession
from app.modules.core import roles_service

router = APIRouter(prefix="/config/roles", tags=["config", "roles"])


class RoleCreateBody(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=1, max_length=120)


class RolePermissionRow(BaseModel):
    module_key: str
    tab_key: str = "*"
    level: str = "none"


class RoleMatrixPutBody(BaseModel):
    modules: list[RolePermissionRow]


@router.get("")
def list_roles(_admin: AdminUser, db: DbSession) -> dict[str, Any]:
    return {"roles": roles_service.list_roles(db)}


@router.post("", status_code=201)
def create_role(body: RoleCreateBody, _admin: AdminUser, db: DbSession) -> dict[str, Any]:
    return roles_service.create_role(db, code=body.code, name=body.name)


@router.get("/{code}")
def get_role_matrix(code: str, _admin: AdminUser, db: DbSession) -> dict[str, Any]:
    return roles_service.get_role_matrix(db, code)


@router.put("/{code}")
def put_role_matrix(
    code: str,
    body: RoleMatrixPutBody,
    _admin: AdminUser,
    db: DbSession,
) -> dict[str, Any]:
    rows = [m.model_dump() for m in body.modules]
    return roles_service.update_role_matrix(db, code, rows)
