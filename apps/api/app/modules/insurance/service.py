"""Báo cáo BH + TNCN theo kỳ (từ payslips)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.core.models import User
from app.modules.insurance.schemas import InsurancePeriodSummary, InsuranceRowOut
from app.modules.attendance.models import PayPeriod
from app.modules.attendance.timesheet import parse_period
from app.modules.mdm.models import Employee
from app.modules.mdm.service import resolve_tax_dependent_count
from app.modules.payroll.models import Payslip, PolicySnapshot
from app.modules.payroll.money import D, ZERO


def si_base_from_payslip_lines(ins: dict, bhxh: Decimal) -> Decimal:
    """Nền đóng BH trên lưới — phiếu mới ghi si_base_charged; phiếu cũ chỉ có si_base_used."""
    if not ins:
        return ZERO
    if "si_base_charged" in ins:
        return D(ins.get("si_base_charged") or 0)
    if bhxh > 0:
        return D(ins.get("si_base_used") or ins.get("si_base_raw") or 0)
    return ZERO


def require_insurance_access(user: User) -> None:
    if user.role == "admin" or user.has_module("insurance"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Trợ Lý AI: bạn không có quyền module Bảo Hiểm.",
    )


def _period_or_404(db: Session, period: str) -> PayPeriod:
    try:
        year, month = parse_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pay = (
        db.query(PayPeriod)
        .filter(PayPeriod.year == year, PayPeriod.month == month)
        .one_or_none()
    )
    if pay is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trợ Lý AI: chưa có kỳ lương {period}. Hãy tính lương trước.",
        )
    return pay


def period_summary(db: Session, period: str) -> InsurancePeriodSummary:
    pay = _period_or_404(db, period)
    slips = db.query(Payslip).filter(Payslip.pay_period_id == pay.id).all()
    pit_flag: bool | None = None
    if slips:
        snap_id = slips[0].policy_snapshot_id
        if snap_id:
            snap = db.get(PolicySnapshot, snap_id)
            if snap and isinstance(snap.payload, dict):
                pit_flag = bool(snap.payload.get("pit_enabled", False))

    tot = {
        "bhxh": ZERO,
        "bhyt": ZERO,
        "bhtn": ZERO,
        "union": ZERO,
        "pit": ZERO,
        "gross": ZERO,
        "net": ZERO,
    }
    for s in slips:
        tot["bhxh"] += Decimal(s.bhxh or 0)
        tot["bhyt"] += Decimal(s.bhyt or 0)
        tot["bhtn"] += Decimal(s.bhtn or 0)
        tot["union"] += Decimal(s.union_fee or 0)
        tot["pit"] += Decimal(s.pit_amount or 0)
        tot["gross"] += Decimal(s.gross or 0)
        tot["net"] += Decimal(s.net or 0)

    return InsurancePeriodSummary(
        period=period,
        employee_count=len(slips),
        total_bhxh=tot["bhxh"],
        total_bhyt=tot["bhyt"],
        total_bhtn=tot["bhtn"],
        total_union_fee=tot["union"],
        total_pit=tot["pit"],
        total_gross=tot["gross"],
        total_net=tot["net"],
        pit_enabled_in_snapshot=pit_flag,
    )


def period_rows(db: Session, period: str) -> list[InsuranceRowOut]:
    pay = _period_or_404(db, period)
    rows = (
        db.query(Payslip, Employee)
        .join(Employee, Employee.id == Payslip.employee_id)
        .filter(Payslip.pay_period_id == pay.id)
        .order_by(Employee.employee_code.asc())
        .all()
    )
    out: list[InsuranceRowOut] = []
    for s, emp in rows:
        lines = s.lines if isinstance(s.lines, dict) else {}
        ins = lines.get("insurance") if isinstance(lines.get("insurance"), dict) else {}
        si_base = si_base_from_payslip_lines(ins if isinstance(ins, dict) else {}, D(s.bhxh or 0))
        out.append(
            InsuranceRowOut(
                employee_id=str(emp.id),
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                si_enrolled=bool(emp.si_enrolled),
                pit_enrolled=bool(emp.pit_enrolled),
                tax_dependent_count=resolve_tax_dependent_count(db, emp.id, as_of=pay.date_to),
                si_base=si_base,
                gross=s.gross,
                bhxh=s.bhxh,
                bhyt=s.bhyt,
                bhtn=s.bhtn,
                union_fee=s.union_fee,
                pit_amount=s.pit_amount,
                net=s.net,
            )
        )
    return out
