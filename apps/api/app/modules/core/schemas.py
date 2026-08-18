"""Schemas auth / user."""

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: UUID
    username: str
    full_name: str
    role: str
    role_code: str | None = None
    is_active: bool = True
    is_locked: bool = False
    must_change_password: bool
    modules: list[str]
    permissions: list[str]

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    modules: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    must_change_password: bool = True
    role_code: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    modules: list[str] | None = None
    permissions: list[str] | None = None
    role_code: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    must_change_password: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageOut(BaseModel):
    detail: str
