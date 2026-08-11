"""Admin CRUD metadata portal_tabs (08, 02§2.4, 10.2#9)."""

from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.modules.audit.service import write_audit
from app.modules.config.models import PortalTab
from app.modules.config.portal_tabs import DEFAULT_PORTAL_TABS, MODULE_KEYS
from app.modules.core.models import User
from app.modules.core.service import seed_portal_tabs


class TabUpdateItem(BaseModel):
    key: str
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    sort_order: int = Field(ge=1, le=99)
    enabled: bool = True


class TabsPutBody(BaseModel):
    tabs: list[TabUpdateItem]


class TabAdminOut(BaseModel):
    key: str
    name: str
    description: str
    sort_order: int
    enabled: bool
    admin_only: bool
    is_system: bool


def list_tabs_admin(db: Session) -> list[TabAdminOut]:
    seed_portal_tabs(db)
    rows = db.query(PortalTab).order_by(PortalTab.sort_order.asc()).all()
    return [
        TabAdminOut(
            key=r.key,
            name=r.title,
            description=r.description or "",
            sort_order=r.sort_order,
            enabled=r.is_enabled,
            admin_only=r.admin_only,
            is_system=r.is_system,
        )
        for r in rows
    ]


def update_tabs(db: Session, body: TabsPutBody, actor: User) -> list[TabAdminOut]:
    seed_portal_tabs(db)
    if not body.tabs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: cần danh sách tabs.",
        )

    incoming = {t.key.strip(): t for t in body.tabs}
    if set(incoming.keys()) != set(MODULE_KEYS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Trợ Lý AI: phải gửi đủ đúng 8 ô hệ thống "
                f"({', '.join(MODULE_KEYS)}). Không thêm/xóa key tùy ý."
            ),
        )

    orders = [t.sort_order for t in body.tabs]
    if len(orders) != len(set(orders)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: sort_order không được trùng.",
        )

    before = {r.key: (r.title, r.sort_order, r.is_enabled) for r in db.query(PortalTab).all()}

    for key, item in incoming.items():
        row = db.get(PortalTab, key)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Trợ Lý AI: không tìm thấy ô «{key}».",
            )
        name = item.name.strip()
        if not name:
            raise HTTPException(
                status_code=400,
                detail=f"Trợ Lý AI: tên ô «{key}» không được trống.",
            )
        if row.is_system and not item.enabled:
            raise HTTPException(
                status_code=400,
                detail="Trợ Lý AI: không được tắt ô Cấu Hình (is_system).",
            )
        row.title = name
        row.description = (item.description or "").strip()
        row.sort_order = int(item.sort_order)
        row.is_enabled = bool(item.enabled)
        # admin_only / key không đổi qua API

    db.commit()
    after_list = list_tabs_admin(db)
    changed = []
    for t in after_list:
        b = before.get(t.key)
        if b and (b[0] != t.name or b[1] != t.sort_order or b[2] != t.enabled):
            changed.append(t.key)

    write_audit(
        db,
        actor=actor,
        action="config.tabs.update",
        entity_type="portal_tabs",
        entity_id="portal",
        summary=f"Cập nhật Portal Tabs ({len(changed)} ô đổi): {', '.join(changed) or '—'}",
        meta={"changed_keys": changed},
    )
    return after_list


def reset_tabs_seed_names(db: Session, actor: User) -> list[TabAdminOut]:
    """Khôi phục tên/mô tả/thứ tự mặc định Hiến pháp (giữ enabled)."""
    seed_portal_tabs(db)
    by_key = {t["key"]: t for t in DEFAULT_PORTAL_TABS}
    for row in db.query(PortalTab).all():
        seed = by_key.get(row.key)
        if not seed:
            continue
        row.title = seed["name"]
        row.description = seed["description"]
        row.sort_order = seed["sort_order"]
        if not row.is_system:
            row.is_enabled = bool(seed["enabled"])
    db.commit()
    write_audit(
        db,
        actor=actor,
        action="config.tabs.reset",
        entity_type="portal_tabs",
        entity_id="portal",
        summary="Khôi phục tên/thứ tự Portal Tabs theo seed Hiến pháp",
    )
    return list_tabs_admin(db)
