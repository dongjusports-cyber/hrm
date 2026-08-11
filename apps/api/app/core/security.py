"""JWT + bcrypt — token staff tách audience (file 12§12.2)."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
AUDIENCE_STAFF = "staff"
AUDIENCE_WORKER = "worker"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(
    *,
    subject: str,
    audience: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "aud": audience,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: UUID, role: str, audience: str = AUDIENCE_STAFF) -> str:
    settings = get_settings()
    return create_token(
        subject=str(user_id),
        audience=audience,
        expires_delta=timedelta(hours=settings.jwt_access_hours),
        extra={"role": role, "typ": "access"},
    )


def create_refresh_token(user_id: UUID, audience: str = AUDIENCE_STAFF) -> str:
    settings = get_settings()
    return create_token(
        subject=str(user_id),
        audience=audience,
        expires_delta=timedelta(days=settings.jwt_refresh_days),
        extra={"typ": "refresh"},
    )


def decode_token(token: str, *, audience: str, expect_typ: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            audience=audience,
        )
    except JWTError as exc:
        raise ValueError("Token không hợp lệ hoặc đã hết hạn.") from exc
    if expect_typ and payload.get("typ") != expect_typ:
        raise ValueError("Loại token không đúng.")
    return payload
