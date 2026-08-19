"""Worker auth — MSNV + mật khẩu mặc định 4 số cuối CCCD/MSNV, khóa 3 lần."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.security import (
    AUDIENCE_WORKER,
    create_access_token,
    hash_password,
    verify_password,
)
from app.modules.core.models import User
from app.modules.mdm.models import Employee, Team
from app.modules.config.mobile_punch import employee_dept_code, get_effective_settings, punch_eligibility
from app.modules.worker.schemas import WorkerOut, WorkerTokenResponse

MAX_FAILED = 3
MSG_INACTIVE = "Tài khoản đã ngưng hoạt động do nhân sự đã nghỉ việc."
MSG_LOCKED = (
    "Tài khoản đã bị khóa do nhập sai mật khẩu 3 lần. "
    "Vui lòng liên hệ phòng Nhân sự (HR) để mở khóa."
)
MSG_ACCOUNT_OTHER_PHONE = (
    "Tài khoản đã khóa trên điện thoại khác. Liên hệ HR để mở khóa máy."
)
MSG_DEVICE_INVALID = "Mã điện thoại không hợp lệ."
_DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")


def normalize_device_id(raw: str) -> str:
    value = (raw or "").strip()
    if not _DEVICE_ID_RE.fullmatch(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEVICE_INVALID)
    return value


def msg_phone_bound_other(msnv: str) -> str:
    return (
        f"Điện thoại này đã khóa với MSNV {msnv}. "
        "Không đăng nhập tài khoản khác. Liên hệ HR nếu đổi máy."
    )


def bind_worker_device(db: Session, user: User, device_id: str) -> None:
    """Lần đầu gắn máy; sau đó máy này không login MSNV khác, MSNV không login máy khác."""
    device_id = normalize_device_id(device_id)
    other = (
        db.query(User)
        .filter(User.worker_device_id == device_id, User.id != user.id)
        .first()
    )
    if other is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg_phone_bound_other(other.username),
        )
    bound = (user.worker_device_id or "").strip()
    if bound and bound != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MSG_ACCOUNT_OTHER_PHONE,
        )
    if not bound:
        user.worker_device_id = device_id


def assert_worker_device_header(db: Session, user: User, device_id: str | None) -> None:
    """Đã gắn máy thì mọi API worker phải đúng mã máy (kể cả thiếu header)."""
    incoming = (device_id or "").strip()
    bound = (user.worker_device_id or "").strip()
    if bound:
        if not incoming or bound != incoming:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=MSG_ACCOUNT_OTHER_PHONE,
            )
        return
    if not incoming:
        return
    other = (
        db.query(User)
        .filter(User.worker_device_id == incoming, User.id != user.id)
        .first()
    )
    if other is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg_phone_bound_other(other.username),
        )


def _digits_only(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def default_password_from_cccd(id_number: str | None, employee_code: str = "") -> str:
    """Mật khẩu mặc định: 4 số cuối CCCD; chưa có CCCD thì 4 số cuối MSNV."""
    cccd_digits = _digits_only(id_number)
    if len(cccd_digits) >= 4:
        return cccd_digits[-4:]
    code_digits = _digits_only(employee_code)
    if len(code_digits) >= 4:
        return code_digits[-4:]
    if code_digits:
        return code_digits.zfill(4)
    return "0000"


def default_worker_password(emp: Employee) -> str:
    return default_password_from_cccd(emp.id_number, emp.employee_code)


def default_worker_reset_password(emp: Employee) -> str:
    """HR mở khóa / tạo tài khoản — bắt buộc đổi lần đăng nhập sau."""
    return default_worker_password(emp)


def worker_to_out(db: Session, user: User, employee_code: str | None = None) -> WorkerOut:
    code = (employee_code or user.username or "").strip()
    emp = _employee_for_user(db, user)
    allowed, reason = punch_eligibility(db, emp, code)
    gps_required = get_effective_settings(db).gps_enforced
    return WorkerOut(
        id=user.id,
        employee_code=code,
        full_name=user.full_name,
        must_change_password=user.must_change_password,
        employee_id=user.employee_id if user.employee_id else (emp.id if emp else None),
        department_code=employee_dept_code(emp),
        can_mobile_punch=allowed,
        punch_blocked_reason=None if allowed else reason,
        gps_required=gps_required,
    )


def _employee_for_user(db: Session, user: User) -> Employee | None:
    q = db.query(Employee).options(joinedload(Employee.team).joinedload(Team.department))
    if user.employee_id is None:
        return q.filter(Employee.employee_code == user.username, Employee.deleted_at.is_(None)).first()
    return q.filter(Employee.id == user.employee_id, Employee.deleted_at.is_(None)).first()


def _assert_worker_may_login(db: Session, user: User) -> None:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_INACTIVE)

    emp = _employee_for_user(db, user)
    if emp is not None and emp.status == "resigned":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_INACTIVE)

    if user.is_locked:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=MSG_LOCKED)


def authenticate_worker(
    db: Session, employee_code: str, password: str, device_id: str
) -> WorkerTokenResponse:
    code = employee_code.strip()
    user = db.query(User).filter(User.username == code, User.role == "worker").first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: MSNV hoặc mật khẩu không đúng.",
        )

    _assert_worker_may_login(db, user)

    if not verify_password(password, user.password_hash):
        user.failed_attempts = int(user.failed_attempts or 0) + 1
        user.failed_login_count = user.failed_attempts
        remaining = MAX_FAILED - user.failed_attempts
        if user.failed_attempts >= MAX_FAILED:
            user.is_locked = True
            user.failed_attempts = MAX_FAILED
            user.failed_login_count = MAX_FAILED
            db.commit()
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=MSG_LOCKED)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Mật khẩu không đúng. Bạn còn {remaining} lần thử.",
        )

    bind_worker_device(db, user, device_id)

    user.failed_attempts = 0
    user.failed_login_count = 0
    user.is_locked = False
    user.locked_until = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Điện thoại này đã khóa với tài khoản khác. Liên hệ HR nếu đổi máy.",
        ) from None

    return WorkerTokenResponse(
        access_token=create_access_token(user.id, "worker", AUDIENCE_WORKER),
        worker=worker_to_out(db, user, code),
    )


def change_worker_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=400,
            detail=f"Trợ Lý AI xin chào {user.full_name}, mật khẩu hiện tại không đúng.",
        )
    emp = _employee_for_user(db, user)
    default_pw = default_worker_password(emp) if emp is not None else ""
    if new_password.strip() == default_pw:
        raise HTTPException(
            status_code=400,
            detail=(
                "Trợ Lý AI: vui lòng chọn mật khẩu mới khác mật khẩu mặc định "
                "(4 số cuối CCCD hoặc MSNV)."
            ),
        )
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: mật khẩu mới phải có ít nhất 6 ký tự.",
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()


def seed_worker_accounts(db: Session) -> int:
    """Tạo tài khoản worker cho NV (MSNV = username, mật khẩu 4 số cuối CCCD/MSNV)."""
    created = 0
    employees = db.query(Employee).filter(Employee.deleted_at.is_(None)).all()
    for emp in employees:
        exists = (
            db.query(User)
            .filter(User.username == emp.employee_code, User.role == "worker")
            .first()
        )
        if exists:
            continue
        db.add(
            User(
                username=emp.employee_code,
                full_name=emp.full_name,
                password_hash=hash_password(default_worker_password(emp)),
                role="worker",
                employee_id=emp.id,
                must_change_password=True,
                is_active=emp.status != "resigned",
            )
        )
        created += 1
    db.commit()
    return created
