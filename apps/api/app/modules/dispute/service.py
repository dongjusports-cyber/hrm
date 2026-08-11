"""Khiếu nại: Worker tạo ticket (P4.3) + inbox assign/đóng (P4.4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.ai.schemas import AiAlertCreate
from app.modules.ai.service import create_alert
from app.modules.attendance.models import PayPeriod
from app.modules.core.models import User
from app.modules.dispute.models import Dispute
from app.modules.dispute.reasons import REASON_CHOICES, REASON_LABELS, is_valid_reason
from app.modules.dispute.schemas import (
    DisputeAssignRequest,
    DisputeCloseRequest,
    DisputeCreateRequest,
    DisputeOut,
    DisputeReasonOut,
)
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from app.modules.worker.payslips import VISIBLE, _expire_if_past_deadline, _require_employee

OPEN_STATUSES = ("open", "ai_reviewed", "hr_pending")


def list_reasons() -> list[DisputeReasonOut]:
    return [DisputeReasonOut(code=c, label=l) for c, l in REASON_CHOICES]


def _next_code(db: Session) -> str:
    n = db.query(Dispute).count() + 1
    for _ in range(20):
        code = f"K{n:03d}"
        if db.query(Dispute).filter(Dispute.code == code).one_or_none() is None:
            return code
        n += 1
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Trợ Lý AI: không tạo được mã khiếu nại. Thử lại.",
    )


def _assignee_name(db: Session, user_id: UUID | None) -> str | None:
    if user_id is None:
        return None
    u = db.get(User, user_id)
    return u.full_name if u else None


def _hr_note_from_description(description: str) -> str | None:
    marker = "\n---\nHR: "
    if marker in description:
        return description.split(marker, 1)[1].strip() or None
    return None


def _to_out(db: Session, d: Dispute, emp: Employee, period: str, payslip_status: str) -> DisputeOut:
    return DisputeOut(
        id=d.id,
        code=d.code,
        payslip_id=d.payslip_id,
        employee_id=d.employee_id,
        employee_code=emp.employee_code,
        employee_name=emp.full_name,
        period=period,
        reason_code=d.reason_code,
        reason_label=REASON_LABELS.get(d.reason_code, d.reason_code),
        description=d.description.split("\n---\nHR: ")[0],
        status=d.status,
        payslip_status=payslip_status,
        assigned_user_id=d.assigned_user_id,
        assigned_user_name=_assignee_name(db, d.assigned_user_id),
        created_at=d.created_at,
        closed_at=d.closed_at,
        hr_note=_hr_note_from_description(d.description),
        ai_summary=d.ai_summary,
    )


def user_can_view_disputes(user: User) -> bool:
    if user.role == "admin":
        return True
    return user.has_module("dispute") or user.has_module("payroll")


def _get_row(db: Session, dispute_id: UUID) -> tuple[Dispute, Employee, PayPeriod, Payslip]:
    row = (
        db.query(Dispute, Employee, PayPeriod, Payslip)
        .join(Employee, Employee.id == Dispute.employee_id)
        .join(Payslip, Payslip.id == Dispute.payslip_id)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .filter(Dispute.id == dispute_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy khiếu nại này.",
        )
    return row


def _eligible_assignee(db: Session, user_id: UUID) -> User:
    u = (
        db.query(User)
        .filter(User.id == user_id, User.is_active.is_(True), User.role.in_(["admin", "user"]))
        .one_or_none()
    )
    if u is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: không tìm thấy người được gán (hoặc tài khoản không hợp lệ).",
        )
    if not user_can_view_disputes(u):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI: {u.full_name} chưa có quyền module Khiếu Nại / Tính Lương — "
                "không gán được."
            ),
        )
    return u


def emit_stale_dispute_alerts(db: Session, *, hours: int = 24) -> int:
    """Rule Lớp A: khiếu nại mở > N giờ chưa đóng → nhắc (05§5.3)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        db.query(Dispute, Employee)
        .join(Employee, Employee.id == Dispute.employee_id)
        .filter(Dispute.status.in_(OPEN_STATUSES), Dispute.created_at <= cutoff)
        .all()
    )
    created = 0
    for d, emp in rows:
        out = create_alert(
            db,
            AiAlertCreate(
                rule_key="dispute_stale",
                title=f"Trợ Lý AI: Khiếu nại {d.code} quá {hours}h chưa xử lý",
                body=(
                    f"{emp.full_name} (MSNV {emp.employee_code}) — "
                    f"{REASON_LABELS.get(d.reason_code, d.reason_code)}. Vào ô Khiếu Nại."
                ),
                target_module="dispute",
                user_id=None,
                source_ref=f"dispute_stale:{d.id}",
            ),
        )
        if out is not None:
            created += 1
    return created


def list_disputes(db: Session, user: User, *, status_filter: str | None = None) -> list[DisputeOut]:
    if not user_can_view_disputes(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền xem khiếu nại.",
        )
    emit_stale_dispute_alerts(db)

    q = (
        db.query(Dispute, Employee, PayPeriod, Payslip)
        .join(Employee, Employee.id == Dispute.employee_id)
        .join(Payslip, Payslip.id == Dispute.payslip_id)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .order_by(Dispute.created_at.desc())
    )
    if status_filter == "open":
        q = q.filter(Dispute.status.in_(OPEN_STATUSES))
    elif status_filter:
        q = q.filter(Dispute.status == status_filter)
    rows = q.limit(200).all()
    return [
        _to_out(db, d, emp, f"{pay.year:04d}-{pay.month:02d}", slip.status)
        for d, emp, pay, slip in rows
    ]


def get_dispute(db: Session, user: User, dispute_id: UUID) -> DisputeOut:
    if not user_can_view_disputes(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền xem khiếu nại.",
        )
    d, emp, pay, slip = _get_row(db, dispute_id)
    return _to_out(db, d, emp, f"{pay.year:04d}-{pay.month:02d}", slip.status)


def assign_dispute(
    db: Session, user: User, dispute_id: UUID, body: DisputeAssignRequest
) -> DisputeOut:
    if not user_can_view_disputes(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền xử lý khiếu nại.",
        )
    d, emp, pay, slip = _get_row(db, dispute_id)
    if d.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: khiếu nại {d.code} đã đóng — không gán lại.",
        )
    target_id = body.user_id or user.id
    assignee = _eligible_assignee(db, target_id)
    d.assigned_user_id = assignee.id
    d.status = "hr_pending"
    db.commit()
    db.refresh(d)
    from app.modules.audit.service import write_audit

    write_audit(
        db,
        actor=user,
        action="dispute.assign",
        entity_type="dispute",
        entity_id=d.code,
        summary=f"Gán khiếu nại {d.code} cho {assignee.full_name}",
        meta={"assignee": assignee.username},
    )
    return _to_out(db, d, emp, f"{pay.year:04d}-{pay.month:02d}", slip.status)


def close_dispute(
    db: Session, user: User, dispute_id: UUID, body: DisputeCloseRequest
) -> DisputeOut:
    """Đóng ticket → phiếu lương resolved (có thể republish ở ô Tính Lương)."""
    if not user_can_view_disputes(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền đóng khiếu nại.",
        )
    d, emp, pay, slip = _get_row(db, dispute_id)
    if d.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: khiếu nại {d.code} đã đóng trước đó.",
        )

    note = (body.note or "").strip()
    if note:
        base = d.description.split("\n---\nHR: ")[0]
        d.description = f"{base}\n---\nHR: {note}"

    if d.assigned_user_id is None:
        d.assigned_user_id = user.id
    d.status = "closed"
    d.closed_at = datetime.now(timezone.utc)
    if slip.status == "disputed":
        slip.status = "resolved"
    db.commit()
    db.refresh(d)
    db.refresh(slip)
    from app.modules.audit.service import write_audit

    write_audit(
        db,
        actor=user,
        action="dispute.close",
        entity_type="dispute",
        entity_id=d.code,
        summary=f"Đóng khiếu nại {d.code} — phiếu → {slip.status}",
        meta={"payslip_status": slip.status, "has_hr_note": bool(note)},
    )
    return _to_out(db, d, emp, f"{pay.year:04d}-{pay.month:02d}", slip.status)


def create_worker_dispute(
    db: Session, worker: User, payslip_id: UUID, body: DisputeCreateRequest
) -> DisputeOut:
    """Worker gửi khiếu nại — không AI. Phiếu → disputed + badge Lớp A."""
    emp_id = _require_employee(worker)
    if not is_valid_reason(body.reason_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, lý do khiếu nại không hợp lệ.",
        )

    row = (
        db.query(Payslip, PayPeriod, Employee)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .filter(Payslip.id == payslip_id, Payslip.employee_id == emp_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, không tìm thấy phiếu lương này.",
        )
    slip, pay, emp = row
    if slip.status not in VISIBLE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, phiếu chưa được HR phát hành.",
        )

    _expire_if_past_deadline(db, slip)

    if slip.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, phiếu đã xác nhận và khóa — "
                "không khiếu nại được."
            ),
        )
    if slip.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, đã quá hạn xác nhận/khiếu nại. "
                "Liên hệ HR."
            ),
        )
    if slip.status == "disputed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, phiếu đang khiếu nại — chờ HR xử lý."
            ),
        )
    if slip.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, chỉ khiếu nại được phiếu "
                "đang chờ xác nhận."
            ),
        )

    open_existing = (
        db.query(Dispute)
        .filter(Dispute.payslip_id == slip.id, Dispute.status != "closed")
        .first()
    )
    if open_existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, đã có khiếu nại {open_existing.code} "
                "cho phiếu này."
            ),
        )

    period = f"{pay.year:04d}-{pay.month:02d}"
    code = _next_code(db)
    dispute = Dispute(
        code=code,
        payslip_id=slip.id,
        employee_id=emp.id,
        reason_code=body.reason_code.strip(),
        description=body.description.strip(),
        status="open",
    )
    slip.status = "disputed"
    db.add(dispute)
    db.commit()
    db.refresh(dispute)

    reason_label = REASON_LABELS.get(dispute.reason_code, dispute.reason_code)
    create_alert(
        db,
        AiAlertCreate(
            rule_key="dispute_new",
            title=f"Trợ Lý AI: Khiếu nại mới {code}",
            body=(
                f"{emp.full_name} (MSNV {emp.employee_code}) kỳ {period}: {reason_label}. "
                f"{dispute.description[:240]}"
            ),
            target_module="dispute",
            user_id=None,
            source_ref=f"dispute:{dispute.id}",
        ),
    )

    return _to_out(db, dispute, emp, period, slip.status)
