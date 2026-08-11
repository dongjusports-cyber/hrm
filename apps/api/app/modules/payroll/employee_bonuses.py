"""Thưởng NV — F_GET_BONUS trong tính lương (4.8)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.payroll.models import EmployeeBonus
from app.modules.payroll.money import D, money_vnd

Q2 = Decimal("0.01")


@dataclass(frozen=True)
class BonusLine:
    bonus_id: UUID
    bonus_code: str
    seq_times: int
    amount: Decimal
    reason: str


@dataclass(frozen=True)
class BonusResult:
    total: Decimal
    lines: list[BonusLine]


def get_bonus_for_period(db: Session, employee_id: UUID, pay_period_id: UUID) -> BonusResult:
    """Tổng thưởng gắn kỳ lương — tương đương F_GET_BONUS(APPLY_FLAG chưa xử lý)."""
    rows = (
        db.query(EmployeeBonus)
        .filter(
            EmployeeBonus.employee_id == employee_id,
            EmployeeBonus.pay_period_id == pay_period_id,
        )
        .order_by(EmployeeBonus.seq_times.asc())
        .all()
    )
    lines: list[BonusLine] = []
    total = Decimal("0")
    for row in rows:
        amt = money_vnd(D(row.bonus_amount))
        if amt <= 0:
            continue
        lines.append(
            BonusLine(
                bonus_id=row.id,
                bonus_code=row.bonus_code,
                seq_times=int(row.seq_times),
                amount=amt,
                reason=row.reason or row.bonus_code,
            )
        )
        total += amt
    return BonusResult(total=money_vnd(total), lines=lines)


def mark_bonuses_applied(db: Session, employee_id: UUID, pay_period_id: UUID) -> int:
    now = datetime.now(tz=timezone.utc)
    rows = (
        db.query(EmployeeBonus)
        .filter(
            EmployeeBonus.employee_id == employee_id,
            EmployeeBonus.pay_period_id == pay_period_id,
            EmployeeBonus.applied_at.is_(None),
        )
        .all()
    )
    for row in rows:
        row.applied_at = now
    return len(rows)


def _resolve_employee(db: Session, employee_code: str) -> Employee:
    code = employee_code.strip()
    emp = (
        db.query(Employee)
        .filter(Employee.employee_code == code, Employee.deleted_at.is_(None))
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(status_code=404, detail=f"Trợ Lý AI: không tìm thấy MSNV '{code}'.")
    return emp


def list_bonuses(
    db: Session,
    *,
    period: str | None = None,
    employee_code: str | None = None,
) -> list[dict]:
    query = db.query(EmployeeBonus, Employee).join(Employee, Employee.id == EmployeeBonus.employee_id)
    if period:
        pay = ensure_pay_period(db, period)
        query = query.filter(EmployeeBonus.pay_period_id == pay.id)
    if employee_code:
        emp = _resolve_employee(db, employee_code)
        query = query.filter(EmployeeBonus.employee_id == emp.id)
    rows = query.order_by(EmployeeBonus.bonus_year.desc(), EmployeeBonus.seq_times.asc()).all()
    return [bonus_to_dict(bonus, emp) for bonus, emp in rows]


def bonus_to_dict(row: EmployeeBonus, emp: Employee | None = None) -> dict:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_code": emp.employee_code if emp else None,
        "full_name": emp.full_name if emp else None,
        "bonus_year": row.bonus_year,
        "seq_times": row.seq_times,
        "bonus_code": row.bonus_code,
        "base_salary": row.base_salary,
        "bonus_rate": row.bonus_rate,
        "bonus_amount": row.bonus_amount,
        "pay_period_id": row.pay_period_id,
        "applied_at": row.applied_at,
        "reason": row.reason,
    }


def create_bonus(
    db: Session,
    *,
    employee_code: str,
    bonus_year: int,
    seq_times: int,
    bonus_amount: Decimal,
    period: str,
    bonus_code: str = "TET",
    base_salary: Decimal | None = None,
    bonus_rate: Decimal | None = None,
    reason: str = "",
    actor: User | None = None,
) -> dict:
    if seq_times < 1:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: seq_times phải ≥ 1.")
    if bonus_amount <= 0:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: bonus_amount phải > 0.")
    emp = _resolve_employee(db, employee_code)
    pay = ensure_pay_period(db, period)
    exists = (
        db.query(EmployeeBonus)
        .filter(
            EmployeeBonus.employee_id == emp.id,
            EmployeeBonus.bonus_year == bonus_year,
            EmployeeBonus.seq_times == seq_times,
        )
        .one_or_none()
    )
    if exists is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Trợ Lý AI: thưởng năm {bonus_year} đợt {seq_times} "
                f"cho MSNV {emp.employee_code} đã tồn tại."
            ),
        )
    row = EmployeeBonus(
        employee_id=emp.id,
        bonus_year=bonus_year,
        seq_times=seq_times,
        bonus_code=bonus_code.strip().upper() or "TET",
        base_salary=base_salary if base_salary is not None else emp.contract_salary,
        bonus_rate=bonus_rate if bonus_rate is not None else Decimal("0"),
        bonus_amount=bonus_amount.quantize(Q2),
        pay_period_id=pay.id,
        reason=(reason or "").strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if actor is not None:
        write_audit(
            db,
            actor=actor,
            action="employee_bonus.create",
            entity_type="employee_bonus",
            entity_id=str(row.id),
            summary=f"Ghi thưởng {bonus_amount} MSNV {emp.employee_code} kỳ {period}",
            meta={"bonus_year": bonus_year, "seq_times": seq_times},
        )
    return bonus_to_dict(row, emp)


def delete_bonus(db: Session, bonus_id: UUID, *, actor: User | None = None) -> dict:
    row = db.get(EmployeeBonus, bonus_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy bản ghi thưởng.")
    if row.applied_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: thưởng đã đẩy vào phiếu lương — không xóa được.",
        )
    emp = db.get(Employee, row.employee_id)
    db.delete(row)
    db.commit()
    if actor is not None and emp is not None:
        write_audit(
            db,
            actor=actor,
            action="employee_bonus.delete",
            entity_type="employee_bonus",
            entity_id=str(bonus_id),
            summary=f"Xóa thưởng MSNV {emp.employee_code} đợt {row.seq_times}/{row.bonus_year}",
        )
    return {"detail": "Đã xóa bản ghi thưởng."}
