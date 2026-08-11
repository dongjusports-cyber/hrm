"""Vai trò × module (2.7) — ma trận quyền lưu DB, user.role_code + ghi đè module_grants."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.modules.config.portal_tabs import DEFAULT_PORTAL_TABS, MODULE_KEYS
from app.modules.core.models import PERMISSION_LEVELS, ROLE_TAB_WILDCARD, Role, RolePermission, User

DEFAULT_ROLES: list[dict[str, Any]] = [
    {"code": "admin", "name": "Quản trị hệ thống", "is_system": True, "sort_order": 1},
    {"code": "hr_staff", "name": "Nhân sự (đầy đủ trừ Cấu Hình)", "is_system": True, "sort_order": 2},
    {"code": "payroll_accountant", "name": "Kế toán lương", "is_system": True, "sort_order": 3},
]


def _default_matrix_for(code: str) -> dict[str, str]:
    """Mức quyền theo module (tab_key=*)."""
    if code == "admin":
        return {k: "edit" for k in MODULE_KEYS}
    if code == "hr_staff":
        return {k: "view" for k in MODULE_KEYS if k != "config"}
    if code == "payroll_accountant":
        return {"payroll": "view"}
    return {}


def seed_roles(db: Session) -> int:
    created = 0
    for spec in DEFAULT_ROLES:
        role = db.get(Role, spec["code"])
        if role is None:
            role = Role(
                code=spec["code"],
                name=spec["name"],
                is_system=spec["is_system"],
                sort_order=spec["sort_order"],
            )
            db.add(role)
            db.flush()
            created += 1
            matrix = _default_matrix_for(spec["code"])
            for mod, level in matrix.items():
                db.add(
                    RolePermission(
                        role_code=role.code,
                        module_key=mod,
                        tab_key=ROLE_TAB_WILDCARD,
                        level=level,
                    )
                )
    db.commit()
    return created


def list_roles(db: Session) -> list[dict[str, Any]]:
    rows = db.query(Role).order_by(Role.sort_order.asc(), Role.code.asc()).all()
    return [
        {
            "code": r.code,
            "name": r.name,
            "is_system": r.is_system,
            "sort_order": r.sort_order,
        }
        for r in rows
    ]


def get_role_matrix(db: Session, code: str) -> dict[str, Any]:
    role = (
        db.query(Role)
        .options(selectinload(Role.permissions))
        .filter(Role.code == code)
        .first()
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy vai trò.")
    by_mod: dict[str, str] = {k: "none" for k in MODULE_KEYS}
    for p in role.permissions:
        if p.tab_key != ROLE_TAB_WILDCARD:
            continue
        if p.module_key in by_mod:
            by_mod[p.module_key] = p.level
    modules = [
        {
            "module_key": k,
            "name": next((t["name"] for t in DEFAULT_PORTAL_TABS if t["key"] == k), k),
            "tab_key": ROLE_TAB_WILDCARD,
            "level": by_mod[k],
        }
        for k in MODULE_KEYS
    ]
    return {"code": role.code, "name": role.name, "is_system": role.is_system, "modules": modules}


def _validate_level(level: str, label: str) -> str:
    lv = (level or "none").lower()
    if lv not in PERMISSION_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Trợ Lý AI: {label} phải là none | view | edit | approve.",
        )
    return lv


def update_role_matrix(db: Session, code: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    role = db.get(Role, code)
    if role is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy vai trò.")
    if code == "admin":
        raise HTTPException(status_code=400, detail="Trợ Lý AI: không sửa ma trận vai trò Admin.")

    role.permissions.clear()
    db.flush()
    seen: set[str] = set()
    for i, row in enumerate(entries):
        mod = str(row.get("module_key", "")).strip()
        if mod not in MODULE_KEYS:
            raise HTTPException(status_code=400, detail=f"Trợ Lý AI: dòng {i + 1} module không hợp lệ.")
        if mod in seen:
            continue
        seen.add(mod)
        tab = str(row.get("tab_key") or ROLE_TAB_WILDCARD)
        level = _validate_level(str(row.get("level", "none")), f"modules[{mod}].level")
        if mod == "config" and level != "none":
            raise HTTPException(
                status_code=400,
                detail="Trợ Lý AI: ô Cấu Hình chỉ dành cho Admin (role_code=admin).",
            )
        if level == "none":
            continue
        db.add(
            RolePermission(
                role_code=code,
                module_key=mod,
                tab_key=tab,
                level=level,
            )
        )
    db.commit()
    return get_role_matrix(db, code)


def create_role(db: Session, *, code: str, name: str) -> dict[str, Any]:
    c = code.strip().lower().replace(" ", "_")
    if not c or len(c) > 40:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: mã vai trò không hợp lệ.")
    if db.get(Role, c):
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: vai trò '{c}' đã tồn tại.")
    max_sort = db.query(Role.sort_order).order_by(Role.sort_order.desc()).limit(1).scalar() or 0
    role = Role(code=c, name=name.strip(), is_system=False, sort_order=int(max_sort) + 1)
    db.add(role)
    db.commit()
    return {"code": role.code, "name": role.name, "is_system": False, "sort_order": role.sort_order}


def assign_user_role_code(db: Session, user: User, role_code: str | None) -> None:
    if role_code is None or role_code == "":
        user.role_code = None
        return
    if user.role == "admin":
        user.role_code = "admin"
        return
    role = db.get(Role, role_code)
    if role is None:
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: vai trò '{role_code}' không tồn tại.")
    if role_code == "admin":
        raise HTTPException(status_code=400, detail="Trợ Lý AI: chỉ tài khoản Admin mới gán vai trò admin.")
    user.role_code = role_code


def validate_role_code(db: Session, role_code: str | None, user_role: str) -> None:
    if not role_code:
        return
    if role_code == "admin" and user_role != "admin":
        raise HTTPException(status_code=400, detail="Trợ Lý AI: vai trò admin chỉ cho tài khoản Admin.")
    if db.get(Role, role_code) is None:
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: vai trò '{role_code}' không tồn tại.")
