"""Auth service — login, khóa sau 3 lần sai, gán quyền."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.security import (
    AUDIENCE_STAFF,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.config.models import PortalTab
from app.modules.config.portal_tabs import DEFAULT_PORTAL_TABS, MODULE_KEYS
from app.modules.core.models import Role, User, UserModuleGrant, UserPermission
from app.modules.core.roles_service import assign_user_role_code, seed_roles, validate_role_code
from app.modules.core.schemas import TokenResponse, UserOut
from app.modules.mdm.models import Employee

MAX_FAILED_LOGINS = 3
MSG_INACTIVE = "Tài khoản đã ngưng hoạt động do nhân sự đã nghỉ việc."
MSG_LOCKED = (
    "Tài khoản đã bị khóa do nhập sai mật khẩu 3 lần. "
    "Vui lòng liên hệ phòng Nhân sự (HR) để mở khóa."
)


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        role_code=user.role_code,
        is_active=user.is_active,
        is_locked=bool(user.is_locked),
        must_change_password=user.must_change_password,
        modules=user.granted_modules(),
        permissions=user.permission_keys(),
    )


def _load_user(db: Session, user_id) -> User:
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
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy người dùng.",
        )
    return user


def _set_modules(db: Session, user: User, module_keys: list[str]) -> None:
    keys = validate_module_grants(user.role, module_keys)
    user.module_grants.clear()
    db.flush()
    if user.role != "admin":
        for key in keys:
            db.add(UserModuleGrant(user_id=user.id, module_key=key))


def _set_permissions(db: Session, user: User, permission_keys: list[str]) -> None:
    allowed = {"ai_query"}
    cleaned: list[str] = []
    for key in permission_keys:
        if key not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trợ Lý AI: quyền '{key}' không hợp lệ.",
            )
        if key not in cleaned:
            cleaned.append(key)
    user.permissions.clear()
    db.flush()
    if user.role == "admin":
        db.add(UserPermission(user_id=user.id, permission_key="ai_query"))
        return
    for key in cleaned:
        db.add(UserPermission(user_id=user.id, permission_key=key))


def get_user_out(db: Session, user_id) -> UserOut:
    return user_to_out(_load_user(db, user_id))


def list_users(db: Session) -> list[UserOut]:
    rows = (
        db.query(User)
        .options(
            selectinload(User.module_grants),
            selectinload(User.permissions),
            selectinload(User.role_entity).selectinload(Role.permissions),
        )
        .filter(User.role.in_(["admin", "user"]))
        .order_by(User.username.asc())
        .all()
    )
    return [user_to_out(u) for u in rows]


def create_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    password: str,
    modules: list[str],
    permissions: list[str],
    must_change_password: bool,
    role_code: str | None = None,
) -> UserOut:
    """Chỉ tạo role=user (Admin hệ thống từ seed — file 02§2.5)."""
    uname = username.strip().lower()
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: tên đăng nhập '{uname}' đã tồn tại.",
        )
    validate_role_code(db, role_code, "user")
    keys = validate_module_grants("user", modules) if modules else []
    user = User(
        username=uname,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role="user",
        must_change_password=must_change_password,
    )
    db.add(user)
    db.flush()
    assign_user_role_code(db, user, role_code)
    if keys:
        for key in keys:
            db.add(UserModuleGrant(user_id=user.id, module_key=key))
    _set_permissions(db, user, permissions)
    db.commit()
    return user_to_out(_load_user(db, user.id))


def update_user(
    db: Session,
    *,
    actor: User,
    user_id,
    full_name: str | None,
    is_active: bool | None,
    modules: list[str] | None,
    permissions: list[str] | None,
    new_password: str | None,
    must_change_password: bool | None,
    role_code: str | None = None,
    role_code_set: bool = False,
) -> UserOut:
    user = _load_user(db, user_id)

    if user.role == "worker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: tài khoản công nhân quản lý ở cổng Worker (P1.5).",
        )

    if full_name is not None:
        user.full_name = full_name.strip()

    if is_active is not None:
        if user.id == actor.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: bạn không thể tự vô hiệu hóa chính mình.",
            )
        if user.role == "admin" and not is_active:
            active_admins = (
                db.query(User)
                .filter(User.role == "admin", User.is_active.is_(True), User.id != user.id)
                .count()
            )
            if active_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Trợ Lý AI: không thể vô hiệu hóa Admin duy nhất của hệ thống.",
                )
        user.is_active = is_active

    if modules is not None:
        if user.role == "admin":
            # Admin luôn 8/8 — bỏ qua gán tay
            pass
        else:
            _set_modules(db, user, modules)

    if permissions is not None and user.role != "admin":
        _set_permissions(db, user, permissions)

    if new_password is not None:
        user.password_hash = hash_password(new_password)
        if must_change_password is None:
            user.must_change_password = True

    if must_change_password is not None:
        user.must_change_password = must_change_password

    if role_code_set and user.role != "admin":
        validate_role_code(db, role_code, user.role)
        assign_user_role_code(db, user, role_code)

    db.commit()
    return user_to_out(_load_user(db, user.id))


def unlock_staff_user(db: Session, *, actor: User, user_id) -> UserOut:
    """Admin mở khóa tài khoản Web (HR) sau 3 lần sai mật khẩu."""
    from app.modules.audit.service import write_audit

    user = _load_user(db, user_id)
    if user.role == "worker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: tài khoản công nhân mở khóa tại Nhân Sự (Reset Mật Khẩu).",
        )
    if user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: chỉ mở khóa tài khoản nhân viên HR (không phải Admin).",
        )

    user.is_locked = False
    user.failed_attempts = 0
    user.failed_login_count = 0
    user.locked_until = None
    write_audit(
        db,
        actor=actor,
        action="user.unlock",
        entity_type="user",
        entity_id=str(user.id),
        summary=f"Mở khóa tài khoản {user.username}",
        commit=False,
    )
    db.commit()
    return user_to_out(_load_user(db, user.id))


def authenticate(db: Session, username: str, password: str) -> TokenResponse:
    user = (
        db.query(User)
        .options(
            selectinload(User.module_grants),
            selectinload(User.permissions),
            selectinload(User.role_entity).selectinload(Role.permissions),
        )
        .filter(User.username == username.strip())
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: tên đăng nhập hoặc mật khẩu không đúng.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MSG_INACTIVE,
        )

    if user.role == "worker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trợ Lý AI: tài khoản công nhân vui lòng đăng nhập tại cổng /worker.",
        )

    if user.employee_id is not None:
        emp = db.get(Employee, user.employee_id)
        if emp is not None and emp.status == "resigned":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=MSG_INACTIVE,
            )

    if user.is_locked:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=MSG_LOCKED)

    if not verify_password(password, user.password_hash):
        user.failed_attempts = int(user.failed_attempts or 0) + 1
        user.failed_login_count = user.failed_attempts
        remaining = MAX_FAILED_LOGINS - user.failed_attempts
        if user.failed_attempts >= MAX_FAILED_LOGINS:
            user.is_locked = True
            user.failed_attempts = MAX_FAILED_LOGINS
            user.failed_login_count = MAX_FAILED_LOGINS
            db.commit()
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=MSG_LOCKED)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Mật khẩu không đúng. Bạn còn {remaining} lần thử.",
        )

    user.failed_attempts = 0
    user.failed_login_count = 0
    user.is_locked = False
    user.locked_until = None
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role, AUDIENCE_STAFF),
        refresh_token=create_refresh_token(user.id, AUDIENCE_STAFF),
        user=user_to_out(user),
    )


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI xin chào {user.full_name}, mật khẩu hiện tại không đúng.",
        )
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: mật khẩu mới phải có ít nhất 8 ký tự.",
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()


def validate_module_grants(role: str, module_keys: list[str]) -> list[str]:
    """User max 7; config chỉ admin (file 02§2.5)."""
    unique = []
    for key in module_keys:
        if key not in MODULE_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trợ Lý AI: module '{key}' không hợp lệ.",
            )
        if key not in unique:
            unique.append(key)

    if role == "admin":
        return list(MODULE_KEYS)

    if "config" in unique:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: ô Cấu Hình chỉ dành cho Admin.",
        )
    if len(unique) > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: user thường được gán tối đa 7 module.",
        )
    return unique


def seed_portal_tabs(db: Session) -> int:
    """Chỉ tạo các ô portal_tabs còn thiếu — KHÔNG ghi đè tên/mô tả ô đã có.

    Trước đây hàm này đồng bộ lại tên/mô tả mỗi lần gọi, nên Admin đổi tên tab (PUT
    /api/config/tabs) rồi gọi lại danh sách là bị ghi đè về mặc định ngay (bug — xem
    test_portal_tabs_config.py::test_admin_rename_and_reorder). Muốn khôi phục tên mặc định
    thì dùng đúng hành động `reset_tabs_seed_names` (nút "Khôi phục mặc định").
    """
    created = 0
    for tab in DEFAULT_PORTAL_TABS:
        existing = db.get(PortalTab, tab["key"])
        if existing:
            continue
        db.add(
            PortalTab(
                key=tab["key"],
                title=tab["name"],
                description=tab["description"],
                icon=tab["key"],
                sort_order=tab["sort_order"],
                is_enabled=tab["enabled"],
                is_system=tab["key"] == "config",
                admin_only=tab["admin_only"],
            )
        )
        created += 1
    db.commit()
    return created


def seed_admin_and_demo(db: Session) -> dict[str, str]:
    """Seed Admin (Chủ) + user HR demo (max 7, không config)."""
    settings = get_settings()
    seed_portal_tabs(db)
    seed_roles(db)

    admin = db.query(User).filter(User.username == settings.admin_username).first()
    if admin is None:
        admin = User(
            username=settings.admin_username,
            full_name=settings.admin_full_name,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            role_code="admin",
            must_change_password=True,
        )
        db.add(admin)
        db.flush()
        db.add(UserPermission(user_id=admin.id, permission_key="ai_query"))
    elif admin.role_code is None:
        admin.role_code = "admin"

    hr = db.query(User).filter(User.username == "hr.demo").first()
    if hr is None:
        hr = User(
            username="hr.demo",
            full_name="Nguyễn Thị HR",
            password_hash=hash_password("HrDemo@123456"),
            role="user",
            role_code="hr_staff",
            must_change_password=False,
        )
        db.add(hr)
        db.flush()
    elif hr.role_code is None:
        hr.role_code = "hr_staff"

    db.commit()
    return {
        "admin": settings.admin_username,
        "hr_demo": "hr.demo",
    }
