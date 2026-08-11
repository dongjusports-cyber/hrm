"""Worker auth — MSNV + mật khẩu mặc định 1234, khóa 3 lần, chặn nghỉ việc."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    AUDIENCE_WORKER,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.worker.schemas import WorkerOut, WorkerTokenResponse

MAX_FAILED = 3
# Mật khẩu mặc định lần đầu — bắt buộc đổi sau khi đăng nhập
DEFAULT_WORKER_PASSWORD = "1234"
MSG_INACTIVE = "Tài khoản đã ngưng hoạt động do nhân sự đã nghỉ việc."
MSG_LOCKED = (
    "Tài khoản đã bị khóa do nhập sai mật khẩu 3 lần. "
    "Vui lòng liên hệ phòng Nhân sự (HR) để mở khóa."
)


def worker_to_out(user: User, employee_code: str) -> WorkerOut:
    return WorkerOut(
        id=user.id,
        employee_code=employee_code,
        full_name=user.full_name,
        must_change_password=user.must_change_password,
        employee_id=user.employee_id,
    )


def _employee_for_user(db: Session, user: User) -> Employee | None:
    if user.employee_id is None:
        return (
            db.query(Employee)
            .filter(Employee.employee_code == user.username, Employee.deleted_at.is_(None))
            .first()
        )
    return (
        db.query(Employee)
        .filter(Employee.id == user.employee_id, Employee.deleted_at.is_(None))
        .first()
    )


def _assert_worker_may_login(db: Session, user: User) -> None:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_INACTIVE)

    emp = _employee_for_user(db, user)
    if emp is not None and emp.status == "resigned":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_INACTIVE)

    if user.is_locked:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=MSG_LOCKED)


def authenticate_worker(db: Session, employee_code: str, password: str) -> WorkerTokenResponse:
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

    user.failed_attempts = 0
    user.failed_login_count = 0
    user.is_locked = False
    user.locked_until = None
    db.commit()

    return WorkerTokenResponse(
        access_token=create_access_token(user.id, "worker", AUDIENCE_WORKER),
        refresh_token=create_refresh_token(user.id, AUDIENCE_WORKER),
        worker=worker_to_out(user, code),
    )


def change_worker_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=400,
            detail=f"Trợ Lý AI xin chào {user.full_name}, mật khẩu hiện tại không đúng.",
        )
    if new_password.strip() == DEFAULT_WORKER_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: vui lòng chọn mật khẩu mới khác mật khẩu mặc định 1234.",
        )
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: mật khẩu mới phải có ít nhất 6 ký tự.",
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()


def default_worker_reset_password() -> str:
    """HR mở khóa / seed — mật khẩu mặc định 1234, bắt buộc đổi lần sau."""
    return DEFAULT_WORKER_PASSWORD


def default_password_from_cccd(id_number: str | None) -> str:
    """Giữ tương thích cũ — ưu tiên mật khẩu mặc định 1234."""
    _ = id_number
    return DEFAULT_WORKER_PASSWORD


def seed_worker_accounts(db: Session) -> int:
    """Tạo tài khoản worker cho NV (MSNV = username, mật khẩu 1234)."""
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
                password_hash=hash_password(DEFAULT_WORKER_PASSWORD),
                role="worker",
                employee_id=emp.id,
                must_change_password=True,
                is_active=emp.status != "resigned",
            )
        )
        created += 1
    db.commit()
    return created
