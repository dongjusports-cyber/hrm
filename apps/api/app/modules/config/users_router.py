"""Users CRUD + gán quyền — chỉ Admin (P1.1 / file 02§2.4 ô User & Quyền)."""

from uuid import UUID

from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.modules.core import service
from app.modules.core.schemas import MessageOut, UserCreate, UserOut, UserUpdate
from app.modules.config.portal_tabs import DEFAULT_PORTAL_TABS, MODULE_KEYS

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(_admin: AdminUser, db: DbSession) -> list[UserOut]:
    return service.list_users(db)


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, _admin: AdminUser, db: DbSession) -> UserOut:
    return service.create_user(
        db,
        username=body.username,
        full_name=body.full_name,
        password=body.password,
        modules=body.modules,
        permissions=body.permissions,
        must_change_password=body.must_change_password,
        role_code=body.role_code,
    )


@router.get("/meta/modules")
def list_assignable_modules(_admin: AdminUser) -> dict:
    """Catalog module để FE vẽ checkbox (không gồm gán config cho user)."""
    items = [
        {
            "key": t["key"],
            "name": t["name"],
            "assignable_to_user": t["key"] != "config",
        }
        for t in DEFAULT_PORTAL_TABS
    ]
    return {"modules": items, "max_user_modules": 7, "all_keys": MODULE_KEYS}


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: UUID, _admin: AdminUser, db: DbSession) -> UserOut:
    return service.get_user_out(db, user_id)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: UUID, body: UserUpdate, admin: AdminUser, db: DbSession) -> UserOut:
    role_set = "role_code" in body.model_fields_set
    return service.update_user(
        db,
        actor=admin,
        user_id=user_id,
        full_name=body.full_name,
        is_active=body.is_active,
        modules=body.modules,
        permissions=body.permissions,
        new_password=body.new_password,
        must_change_password=body.must_change_password,
        role_code=body.role_code,
        role_code_set=role_set,
    )


@router.post("/{user_id}/deactivate", response_model=MessageOut)
def deactivate_user(user_id: UUID, admin: AdminUser, db: DbSession) -> MessageOut:
    user = service.update_user(
        db,
        actor=admin,
        user_id=user_id,
        full_name=None,
        is_active=False,
        modules=None,
        permissions=None,
        new_password=None,
        must_change_password=None,
    )
    return MessageOut(detail=f"Trợ Lý AI: đã vô hiệu hóa tài khoản {user.username}.")
