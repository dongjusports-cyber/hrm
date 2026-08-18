"""
Payslip adjustments — Re-Pay / truy lĩnh / tạm ứng (10.3#15, 03§3.6–3.8).
addon → other_adjustments (cộng gross)
deduction → other_deductions (trừ net)
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from app.modules.attendance.timesheet import ensure_pay_period, get_pay_period
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.payroll.models import PayslipAdjustment
from app.modules.payroll.money import D, ZERO, money_vnd

ALLOWED_KINDS = frozenset({"addon", "deduction"})


class AdjustmentCreate(BaseModel):
    period: str
    employee_code: str
    kind: str  # addon | deduction
    reason: str
    amount: Decimal

    @field_validator("amount", mode="before")
    @classmethod
    def amount_dec(cls, v):  # noqa: ANN001
        return Decimal(str(v))


class AdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    period: str
    employee_id: UUID
    employee_code: str
    full_name: str
    kind: str
    reason: str
    amount: Decimal
    created_by: str
    created_at: str | None


def _assert_editable(period_status: str) -> None:
    if period_status in ("published", "locked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: kỳ đã phát hành/khóa — không sửa điều chỉnh. Mở lại kỳ (phase sau) hoặc nhập trước khi phát hành.",
        )


def sums_for_employee(
    db: Session, pay_period_id: UUID, employee_id: UUID
) -> tuple[Decimal, Decimal, list[dict]]:
    """Trả (other_adjustments, other_deductions, chi tiết)."""
    rows = (
        db.query(PayslipAdjustment)
        .filter(
            PayslipAdjustment.pay_period_id == pay_period_id,
            PayslipAdjustment.employee_id == employee_id,
        )
        .all()
    )
    addon = ZERO
    deduct = ZERO
    detail: list[dict] = []
    for r in rows:
        amt = money_vnd(D(r.amount))
        if r.kind == "addon":
            addon += amt
        else:
            deduct += amt
        detail.append(
            {
                "id": str(r.id),
                "kind": r.kind,
                "reason": r.reason,
                "amount": str(amt),
            }
        )
    return money_vnd(addon), money_vnd(deduct), detail


def list_adjustments(db: Session, period: str, employee_code: str | None = None) -> list[AdjustmentOut]:
    pay = get_pay_period(db, period)
    if pay is None:
        return []
    q = (
        db.query(PayslipAdjustment, Employee, User)
        .join(Employee, Employee.id == PayslipAdjustment.employee_id)
        .join(User, User.id == PayslipAdjustment.created_by_user_id)
        .filter(PayslipAdjustment.pay_period_id == pay.id)
        .order_by(PayslipAdjustment.created_at.desc())
    )
    if employee_code:
        q = q.filter(Employee.employee_code == employee_code.strip())
    out: list[AdjustmentOut] = []
    for row, emp, user in q.all():
        out.append(
            AdjustmentOut(
                id=row.id,
                period=period,
                employee_id=emp.id,
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                kind=row.kind,
                reason=row.reason,
                amount=row.amount,
                created_by=user.username,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
        )
    return out


def create_adjustment(db: Session, body: AdjustmentCreate, user: User) -> AdjustmentOut:
    pay = ensure_pay_period(db, body.period)
    _assert_editable(pay.status)

    kind = body.kind.strip().lower()
    if kind not in ALLOWED_KINDS:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: kind phải là addon (cộng gross) hoặc deduction (trừ net).",
        )
    amount = money_vnd(D(body.amount))
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: số tiền điều chỉnh phải > 0.",
        )
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: cần lý do (vd Truy lĩnh T9, Tạm ứng…).",
        )

    emp = (
        db.query(Employee)
        .filter(
            Employee.employee_code == body.employee_code.strip(),
            Employee.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trợ Lý AI: không tìm thấy MSNV {body.employee_code}.",
        )

    row = PayslipAdjustment(
        pay_period_id=pay.id,
        employee_id=emp.id,
        kind=kind,
        reason=reason[:200],
        amount=amount,
        created_by_user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(
        db,
        actor=user,
        action="payroll.adjust.create",
        entity_type="payslip_adjustment",
        entity_id=str(row.id),
        summary=f"Điều chỉnh {kind} {amount}đ cho {emp.employee_code} kỳ {body.period}",
        meta={"kind": kind, "amount": str(amount), "reason": reason[:120]},
    )
    return AdjustmentOut(
        id=row.id,
        period=body.period,
        employee_id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        kind=row.kind,
        reason=row.reason,
        amount=row.amount,
        created_by=user.username,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


def delete_adjustment(db: Session, adjustment_id: UUID, user: User) -> dict:
    row = db.get(PayslipAdjustment, adjustment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy điều chỉnh.")
    from app.modules.attendance.models import PayPeriod

    pay = db.get(PayPeriod, row.pay_period_id)
    assert pay is not None
    _assert_editable(pay.status)
    period = f"{pay.year:04d}-{pay.month:02d}"
    emp = db.get(Employee, row.employee_id)
    meta = {
        "kind": row.kind,
        "amount": str(row.amount),
        "employee_code": emp.employee_code if emp else None,
        "reason": row.reason,
    }
    adj_id = str(row.id)
    db.delete(row)
    db.commit()
    write_audit(
        db,
        actor=user,
        action="payroll.adjust.delete",
        entity_type="payslip_adjustment",
        entity_id=adj_id,
        summary=f"Xóa điều chỉnh {meta['kind']} kỳ {period}",
        meta=meta,
    )
    return {"ok": True, "message": f"Đã xóa điều chỉnh (bởi {user.username}).", "period": period}
