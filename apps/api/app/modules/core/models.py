"""Models auth / RBAC (schema 07§7.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.config.portal_tabs import MODULE_KEYS

PERMISSION_LEVELS = ("none", "view", "edit", "approve")
ROLE_TAB_WILDCARD = "*"


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="role_entity")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_code: Mapped[str] = mapped_column(
        String(40), ForeignKey("roles.code", ondelete="CASCADE"), primary_key=True
    )
    module_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    tab_key: Mapped[str] = mapped_column(String(40), primary_key=True, default=ROLE_TAB_WILDCARD)
    level: Mapped[str] = mapped_column(String(10), nullable=False, default="none")

    role: Mapped[Role] = relationship(back_populates="permissions")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # admin | user | worker
    role_code: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("roles.code", ondelete="SET NULL"), nullable=True, index=True
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Cột cũ (tương thích) — logic mới dùng failed_attempts / is_locked
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    module_grants: Mapped[list[UserModuleGrant]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    permissions: Mapped[list[UserPermission]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    role_entity: Mapped[Role | None] = relationship(back_populates="users")

    def _modules_from_role(self) -> set[str]:
        if not self.role_code or self.role_entity is None:
            return set()
        out: set[str] = set()
        for p in self.role_entity.permissions:
            if p.level == "none":
                continue
            if p.module_key not in MODULE_KEYS:
                continue
            if p.module_key == "config" and self.role != "admin":
                continue
            out.add(p.module_key)
        return out

    def granted_modules(self) -> list[str]:
        if self.role == "admin":
            return list(MODULE_KEYS)
        modules = self._modules_from_role()
        if not modules:
            modules = {g.module_key for g in self.module_grants}
        else:
            for g in self.module_grants:
                modules.add(g.module_key)
        return sorted(modules)

    def permission_keys(self) -> list[str]:
        if self.role == "admin":
            return ["ai_query"]
        return [p.permission_key for p in self.permissions]

    def has_module(self, module_key: str) -> bool:
        if module_key == "config" and self.role != "admin":
            return False
        return module_key in self.granted_modules()

    def has_permission(self, permission_key: str) -> bool:
        if self.role == "admin":
            return True
        return any(p.permission_key == permission_key for p in self.permissions)


class UserModuleGrant(Base):
    __tablename__ = "user_module_grants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    module_key: Mapped[str] = mapped_column(String(40), primary_key=True)

    user: Mapped[User] = relationship(back_populates="module_grants")


class UserPermission(Base):
    __tablename__ = "user_permissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    permission_key: Mapped[str] = mapped_column(String(40), primary_key=True)

    user: Mapped[User] = relationship(back_populates="permissions")
