"""Portal tabs metadata API — luôn trả đủ 8 ô + allowed theo RBAC (P6)."""

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.modules.config.mobile_punch import (
    MobilePunchSettingsOut,
    MobilePunchSettingsUpdate,
    settings_out,
    update_settings,
)
from app.modules.config.models import PortalTab
from app.modules.config.portal_tabs import DEFAULT_PORTAL_TABS
from app.modules.config.tabs_service import (
    TabAdminOut,
    TabsPutBody,
    list_tabs_admin,
    reset_tabs_seed_names,
    update_tabs,
)

router = APIRouter(tags=["portal"])


@router.get("/portal/tabs")
def get_portal_tabs(db: DbSession, user: CurrentUser) -> dict:
    rows = (
        db.query(PortalTab)
        .filter(PortalTab.is_enabled.is_(True))
        .order_by(PortalTab.sort_order.asc())
        .all()
    )

    if rows:
        tabs = [
            {
                "key": row.key,
                "name": row.title,
                "description": row.description,
                "sort_order": row.sort_order,
                "enabled": row.is_enabled,
                "admin_only": row.admin_only,
                "allowed": user.has_module(row.key),
            }
            for row in rows
        ]
    else:
        # Fallback seed tĩnh nếu chưa chạy seed
        tabs = [
            {
                **tab,
                "allowed": user.has_module(tab["key"]),
            }
            for tab in DEFAULT_PORTAL_TABS
            if tab["enabled"]
        ]

    return {"tabs": tabs, "user_full_name": user.full_name}


@router.get("/config/tabs", response_model=list[TabAdminOut], tags=["config"])
def config_tabs_list(_admin: AdminUser, db: DbSession) -> list[TabAdminOut]:
    """Admin — danh sách đủ 8 ô (kể cả đang tắt)."""
    return list_tabs_admin(db)


@router.put("/config/tabs", response_model=list[TabAdminOut], tags=["config"])
def config_tabs_put(
    body: TabsPutBody,
    admin: AdminUser,
    db: DbSession,
) -> list[TabAdminOut]:
    """Admin — đổi tên / mô tả / thứ tự / bật-tắt (08)."""
    return update_tabs(db, body, admin)


@router.post("/config/tabs/reset", response_model=list[TabAdminOut], tags=["config"])
def config_tabs_reset(admin: AdminUser, db: DbSession) -> list[TabAdminOut]:
    """Admin — khôi phục tên/thứ tự seed Hiến pháp."""
    return reset_tabs_seed_names(db, admin)


@router.get("/config/mobile-punch", response_model=MobilePunchSettingsOut, tags=["config"])
def config_mobile_punch_get(_admin: AdminUser, db: DbSession) -> MobilePunchSettingsOut:
    return settings_out(db)


@router.put("/config/mobile-punch", response_model=MobilePunchSettingsOut, tags=["config"])
def config_mobile_punch_put(
    body: MobilePunchSettingsUpdate,
    _admin: AdminUser,
    db: DbSession,
) -> MobilePunchSettingsOut:
    return update_settings(db, body)
