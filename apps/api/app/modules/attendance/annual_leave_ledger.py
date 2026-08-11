"""Sổ phép năm — bút toán (4.7, 22§22.7)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.attendance.models import AnnualLeaveEntry, AnnualLeaveLedger, LeaveRequest
from app.modules.mdm.models import Employee
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload

Q2 = Decimal("0.01")
KIND_ACCRUAL = "accrual"
KIND_USE = "use"
KIND_ADJUST = "adjust"
KIND_PAYOUT = "payout"


def _annual_days_per_year(db: Session) -> int:
    fallback = int(default_payload()["annual_leave"]["days_per_year"])
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        al = pkg.payload.get("annual_leave")
        if isinstance(al, dict):
            try:
                return int(al.get("days_per_year", fallback))
            except (TypeError, ValueError):
                pass
    return fallback


def _signed_days(kind: str, days: Decimal) -> Decimal:
    raw = abs(days).quantize(Q2, rounding=ROUND_HALF_UP)
    if kind in (KIND_USE, KIND_PAYOUT):
        return -raw
    if kind == KIND_ACCRUAL:
        return raw
    return days.quantize(Q2, rounding=ROUND_HALF_UP)


def ensure_ledger(db: Session, employee_id: UUID, year: int) -> AnnualLeaveLedger:
    row = (
        db.query(AnnualLeaveLedger)
        .filter(AnnualLeaveLedger.employee_id == employee_id, AnnualLeaveLedger.year == year)
        .one_or_none()
    )
    if row is not None:
        return row
    row = AnnualLeaveLedger(
        employee_id=employee_id,
        year=year,
        opening_balance=Decimal("0"),
        accrued=Decimal("0"),
        used=Decimal("0"),
        adjusted=Decimal("0"),
        closing_balance=Decimal("0"),
    )
    db.add(row)
    db.flush()
    return row


def _entry_exists(db: Session, ledger_id: UUID, reference: str) -> bool:
    return (
        db.query(AnnualLeaveEntry.id)
        .filter(AnnualLeaveEntry.ledger_id == ledger_id, AnnualLeaveEntry.reference == reference)
        .first()
        is not None
    )


def _refresh_ledger_summary(db: Session, ledger: AnnualLeaveLedger) -> None:
    rows = db.query(AnnualLeaveEntry).filter(AnnualLeaveEntry.ledger_id == ledger.id).all()
    accrued = Decimal("0")
    used = Decimal("0")
    adjusted = Decimal("0")
    movement = Decimal("0")
    last_accrual_month: int | None = None
    for row in rows:
        signed = _signed_days(row.kind, row.days)
        movement += signed
        if row.kind == KIND_ACCRUAL:
            accrued += abs(signed)
            last_accrual_month = max(last_accrual_month or 0, row.entry_date.month)
        elif row.kind == KIND_USE:
            used += abs(signed)
        elif row.kind == KIND_ADJUST:
            adjusted += signed
    ledger.accrued = accrued.quantize(Q2, rounding=ROUND_HALF_UP)
    ledger.used = used.quantize(Q2, rounding=ROUND_HALF_UP)
    ledger.adjusted = adjusted.quantize(Q2, rounding=ROUND_HALF_UP)
    ledger.closing_balance = (ledger.opening_balance + movement).quantize(Q2, rounding=ROUND_HALF_UP)
    ledger.last_accrued_month = last_accrual_month


def add_entry(
    db: Session,
    ledger: AnnualLeaveLedger,
    *,
    kind: str,
    days: Decimal,
    entry_date: date,
    reference: str | None = None,
    note: str = "",
) -> AnnualLeaveEntry | None:
    if reference and _entry_exists(db, ledger.id, reference):
        return None
    signed = _signed_days(kind, days)
    if signed == 0:
        return None
    row = AnnualLeaveEntry(
        ledger_id=ledger.id,
        entry_date=entry_date,
        kind=kind,
        days=abs(days).quantize(Q2, rounding=ROUND_HALF_UP),
        reference=reference,
        note=note,
    )
    db.add(row)
    db.flush()
    _refresh_ledger_summary(db, ledger)
    return row


def _accrual_months(emp: Employee, as_of: date) -> int:
    year_start = date(as_of.year, 1, 1)
    accrual_start = year_start
    if emp.join_date and emp.join_date > accrual_start:
        accrual_start = emp.join_date
    if accrual_start > as_of:
        return 0
    months = (as_of.year - accrual_start.year) * 12 + (as_of.month - accrual_start.month) + 1
    return max(0, min(12, months))


def sync_accrual(db: Session, emp: Employee, as_of: date) -> AnnualLeaveLedger:
    """Đồng bộ tích lũy phép đến tháng của `as_of` — round(months × days/12, 2)."""
    ledger = ensure_ledger(db, emp.id, as_of.year)
    months = _accrual_months(emp, as_of)
    if months <= 0:
        return ledger
    days_per_year = _annual_days_per_year(db)
    target = (Decimal(months) * Decimal(days_per_year) / Decimal(12)).quantize(
        Q2, rounding=ROUND_HALF_UP
    )
    current = ledger.accrued
    delta = (target - current).quantize(Q2, rounding=ROUND_HALF_UP)
    if delta > 0:
        add_entry(
            db,
            ledger,
            kind=KIND_ACCRUAL,
            days=delta,
            entry_date=as_of,
            reference=f"accrual-{as_of.year}-through-{months:02d}",
            note=f"Tích lũy đến tháng {months}/{as_of.year}",
        )
    return ledger


def record_leave_use(
    db: Session,
    *,
    employee_id: UUID,
    leave_request_id: UUID,
    days: Decimal,
    entry_date: date,
) -> None:
    emp = db.get(Employee, employee_id)
    if emp is None:
        return
    ledger = sync_accrual(db, emp, entry_date)
    add_entry(
        db,
        ledger,
        kind=KIND_USE,
        days=days,
        entry_date=entry_date,
        reference=f"leave_request:{leave_request_id}",
        note="Duyệt đơn phép năm",
    )


def ledger_balance_from_entries(db: Session, ledger_id: UUID) -> Decimal:
    ledger = db.get(AnnualLeaveLedger, ledger_id)
    if ledger is None:
        return Decimal("0")
    rows = db.query(AnnualLeaveEntry).filter(AnnualLeaveEntry.ledger_id == ledger_id).all()
    movement = sum(_signed_days(r.kind, r.days) for r in rows)
    return (ledger.opening_balance + movement).quantize(Q2, rounding=ROUND_HALF_UP)


def pending_submitted_days(db: Session, employee_id: UUID, year: int) -> Decimal:
    used = (
        db.query(func.coalesce(func.sum(LeaveRequest.total_days), 0))
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_code == "ALE",
            LeaveRequest.status == "submitted",
            LeaveRequest.from_date >= date(year, 1, 1),
            LeaveRequest.from_date <= date(year, 12, 31),
        )
        .scalar()
    )
    return Decimal(str(used or 0)).quantize(Q2, rounding=ROUND_HALF_UP)


def annual_leave_remaining(db: Session, employee_id: UUID, as_of: date | None = None) -> Decimal:
    """Số phép còn = sổ bút toán − đơn ALE đang chờ duyệt."""
    as_of = as_of or date.today()
    emp = db.get(Employee, employee_id)
    if emp is None:
        return Decimal("0")
    ledger = sync_accrual(db, emp, as_of)
    balance = ledger.closing_balance
    pending = pending_submitted_days(db, employee_id, as_of.year)
    remaining = (balance - pending).quantize(Q2, rounding=ROUND_HALF_UP)
    return max(Decimal("0"), remaining)


def verify_annual_leave_nghiem_thu_47(
    db: Session,
    *,
    employee_id: UUID,
    as_of: date,
    payslip_remaining: Decimal,
) -> tuple[bool, str]:
    """
    24§ nghiệm thu 4.7 — số phép trên phiếu khớp sổ bút toán.
    closing_balance phải bằng tổng các dòng; phiếu dùng cùng hàm annual_leave_remaining.
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        return False, "Không tìm thấy NV"
    ledger = sync_accrual(db, emp, as_of)
    sum_entries = ledger_balance_from_entries(db, ledger.id)
    closing_ok = ledger.closing_balance.quantize(Q2) == sum_entries.quantize(Q2)
    expected = annual_leave_remaining(db, employee_id, as_of)
    slip_rem = Decimal(str(payslip_remaining)).quantize(Q2, rounding=ROUND_HALF_UP)
    payslip_ok = slip_rem == expected.quantize(Q2)
    ok = closing_ok and payslip_ok
    detail = (
        f"MSNV {emp.employee_code}: sổ={sum_entries} closing={ledger.closing_balance} "
        f"phiếu={slip_rem} kỳ_vọng={expected}"
    )
    if not closing_ok:
        detail += " — lệch sổ/closing"
    if not payslip_ok:
        detail += " — lệch phiếu/hàm"
    return ok, detail
