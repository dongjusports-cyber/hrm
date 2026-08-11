"""Dependencies: DB session, current user, RBAC guards."""

from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import AUDIENCE_STAFF, AUDIENCE_WORKER, decode_token
from app.modules.core.models import Role, User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _denied_detail(full_name: str) -> str:
    return (
        f"Trợ Lý AI xin chào {full_name}, bạn không có quyền truy cập. "
        "Vui lòng liên hệ Admin."
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: bạn chưa đăng nhập. Vui lòng đăng nhập lại.",
        )
    try:
        payload = decode_token(
            credentials.credentials,
            audience=AUDIENCE_STAFF,
            expect_typ="access",
        )
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        ) from None

    user = (
        db.query(User)
        .options(
            selectinload(User.module_grants),
            selectinload(User.permissions),
            selectinload(User.role_entity).selectinload(Role.permissions),
        )
        .filter(User.id == user_id)
        .first()
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: tài khoản không tồn tại hoặc đã bị khóa.",
        )
    if user.role == "worker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trợ Lý AI: tài khoản công nhân chỉ dùng cổng /worker.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_denied_detail(user.full_name),
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_module(module_key: str) -> Callable[[CurrentUser], User]:
    def _guard(user: CurrentUser) -> User:
        if not user.has_module(module_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_denied_detail(user.full_name),
            )
        return user

    return _guard


def require_permission(permission_key: str) -> Callable[[CurrentUser], User]:
    def _guard(user: CurrentUser) -> User:
        if not user.has_permission(permission_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_denied_detail(user.full_name),
            )
        return user

    return _guard


def optional_confirm_step(
    x_confirm_step: Annotated[int | None, Header(alias="X-Confirm-Step")] = None,
) -> int | None:
    """Dùng sau cho lưu policy tiền (P10) — 1|2|3."""
    return x_confirm_step


def get_current_worker(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """JWT audience=worker — tách khỏi Portal staff (file 12§12.2)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: bạn chưa đăng nhập. Vui lòng đăng nhập lại.",
        )
    try:
        payload = decode_token(
            credentials.credentials,
            audience=AUDIENCE_WORKER,
            expect_typ="access",
        )
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        ) from None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: tài khoản không tồn tại hoặc đã bị khóa.",
        )
    if user.role != "worker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trợ Lý AI: cổng công nhân chỉ dành cho tài khoản worker.",
        )
    return user


CurrentWorker = Annotated[User, Depends(get_current_worker)]
