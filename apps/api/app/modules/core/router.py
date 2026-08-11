"""Auth API — login / me / change-password (file 08§8.2)."""

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession
from app.modules.core import service
from app.modules.core.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageOut,
    TokenResponse,
    UserOut,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    return service.authenticate(db, body.username, body.password)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return service.user_to_out(user)


@router.post("/auth/change-password", response_model=MessageOut)
def change_password(body: ChangePasswordRequest, db: DbSession, user: CurrentUser) -> MessageOut:
    service.change_password(db, user, body.current_password, body.new_password)
    return MessageOut(detail=f"Trợ Lý AI xin chào {user.full_name}, đã đổi mật khẩu thành công.")


@router.get("/auth/ping")
def auth_ping() -> dict[str, str]:
    return {"detail": "Auth module P0.4 sẵn sàng."}
