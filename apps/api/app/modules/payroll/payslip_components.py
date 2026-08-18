"""Ghi payslip_components khi tính lương (hạng mục 4.1)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.payroll.engine_allowances import AllowanceResult
from app.modules.payroll.employee_bonuses import BonusResult
from app.modules.payroll.engine_insurance import InsuranceResult
from app.modules.payroll.engine_leave_pay import LeavePayResult
from app.modules.payroll.engine_ot import OtResult
from app.modules.payroll.engine_wd import WdSalaryInput, WdSalaryResult, split_worked_by_contract
from app.modules.payroll.models import PayComponent, PayslipComponent
from app.modules.payroll.money import D, ZERO, money_vnd


@dataclass(frozen=True)
class ComponentDraft:
    component_code: str
    segment: str
    seq_no: int
    amount: Decimal
    quantity: Decimal | None = None
    unit: str | None = None
    unit_amount: Decimal | None = None
    note: str | None = None
    sort_order: int = 0


def _wd_parts(inp: WdSalaryInput, wd_res: WdSalaryResult) -> list[ComponentDraft]:
    divisor = D(inp.salary_divisor)
    contract_days, probation_days = split_worked_by_contract(inp)
    out: list[ComponentDraft] = []
    sort = 10
    if wd_res.probation_amount > 0:
        out.append(
            ComponentDraft(
                component_code="WD",
                segment="probation",
                seq_no=1,
                quantity=probation_days,
                unit="day",
                unit_amount=money_vnd((D(inp.probation_salary) + D(inp.sal_allow)) / divisor)
                if divisor
                else None,
                amount=wd_res.probation_amount,
                note="Lương ngày công thử việc",
                sort_order=sort,
            )
        )
        sort += 10
    if wd_res.official_amount > 0:
        out.append(
            ComponentDraft(
                component_code="WD",
                segment="official",
                seq_no=1,
                quantity=contract_days,
                unit="day",
                unit_amount=money_vnd((D(inp.contract_salary) + D(inp.sal_allow)) / divisor)
                if divisor
                else None,
                amount=wd_res.official_amount,
                note="Lương ngày công chính thức",
                sort_order=sort,
            )
        )
    return out


def _leave_parts(leave_res: LeavePayResult, *, sort_start: int) -> list[ComponentDraft]:
    rows: list[ComponentDraft] = []
    sort = sort_start
    for ln in leave_res.lines:
        rows.append(
            ComponentDraft(
                component_code=ln.leave_code,
                segment=ln.segment,
                seq_no=ln.seq_no,
                quantity=ln.days,
                unit="day",
                amount=ln.amount,
                note=f"{ln.leave_name} ({ln.pay_ratio_percent}%)",
                sort_order=sort,
            )
        )
        sort += 3
    return rows


def build_component_drafts(
    *,
    wd_inp: WdSalaryInput,
    wd_res: WdSalaryResult,
    leave_res: LeavePayResult,
    allow_res: AllowanceResult,
    ot_res: OtResult,
    ins_res: InsuranceResult,
    adj_detail: list[dict],
    bonus_res: BonusResult | None = None,
) -> list[ComponentDraft]:
    """Sinh các dòng chi tiết — mỗi khoản một dòng, có segment + seq_no."""
    rows: list[ComponentDraft] = []
    rows.extend(_wd_parts(wd_inp, wd_res))
    sort = 25
    rows.extend(_leave_parts(leave_res, sort_start=sort))
    if leave_res.lines:
        sort = 25 + len(leave_res.lines) * 3
    else:
        sort = 30

    for ln in allow_res.lines:
        if D(ln.amount) <= 0:
            continue
        rows.append(
            ComponentDraft(
                component_code=ln.code,
                segment="official",
                seq_no=1,
                amount=ln.amount,
                note=ln.name,
                sort_order=sort,
            )
        )
        sort += 5

    ot_parts = ot_res.detail.get("parts") or []
    if ot_parts:
        for i, part in enumerate(ot_parts, start=1):
            raw = D(part.get("raw", "0"))
            if raw <= 0:
                continue
            rows.append(
                ComponentDraft(
                    component_code="OT",
                    segment="official",
                    seq_no=i,
                    quantity=D(part.get("hours", "0")),
                    unit="hour",
                    amount=money_vnd(raw),
                    note=f"OT {part.get('type', '')} ×{part.get('rate', '')}",
                    sort_order=sort,
                )
            )
            sort += 2
    elif ot_res.ot_pay > 0:
        rows.append(
            ComponentDraft(
                component_code="OT",
                segment="official",
                seq_no=1,
                amount=ot_res.ot_pay,
                note="Tăng ca",
                sort_order=sort,
            )
        )
        sort += 5

    for i, adj in enumerate(adj_detail, start=1):
        amt = D(adj.get("amount", "0"))
        if amt == 0:
            continue
        signed = amt if adj.get("kind") == "addon" else -amt
        rows.append(
            ComponentDraft(
                component_code="ADJUST",
                segment="official",
                seq_no=i,
                amount=money_vnd(signed),
                note=str(adj.get("reason") or adj.get("kind") or ""),
                sort_order=sort,
            )
        )
        sort += 3

    if bonus_res and bonus_res.lines:
        for ln in bonus_res.lines:
            rows.append(
                ComponentDraft(
                    component_code="BONUS",
                    segment="official",
                    seq_no=ln.seq_times,
                    amount=ln.amount,
                    note=ln.reason or ln.bonus_code,
                    sort_order=sort,
                )
            )
            sort += 4
    elif bonus_res and bonus_res.total > 0:
        rows.append(
            ComponentDraft(
                component_code="BONUS",
                segment="official",
                seq_no=1,
                amount=bonus_res.total,
                note="Tiền thưởng",
                sort_order=sort,
            )
        )
        sort += 4

    for code, val, note in (
        ("BHXH", ins_res.bhxh, "BHXH 8%"),
        ("BHYT", ins_res.bhyt, "BHYT 1.5%"),
        ("BHTN", ins_res.bhtn, "BHTN 1%"),
        ("UNION", ins_res.union_fee, "Phí công đoàn"),
        ("PIT", ins_res.pit_amount, "Thuế TNCN"),
    ):
        if D(val) <= 0:
            continue
        rows.append(
            ComponentDraft(
                component_code=code,
                segment="official",
                seq_no=1,
                amount=money_vnd(D(val)),
                note=note,
                sort_order=sort,
            )
        )
        sort += 2

    return rows


def replace_payslip_components(db: Session, payslip_id: UUID, drafts: list[ComponentDraft]) -> int:
    db.query(PayslipComponent).filter(PayslipComponent.payslip_id == payslip_id).delete(
        synchronize_session=False
    )
    for d in drafts:
        db.add(
            PayslipComponent(
                payslip_id=payslip_id,
                component_code=d.component_code,
                segment=d.segment,
                seq_no=d.seq_no,
                quantity=d.quantity,
                unit=d.unit,
                unit_amount=d.unit_amount,
                amount=d.amount,
                note=d.note,
                sort_order=d.sort_order,
            )
        )
    return len(drafts)


def list_payslip_components(db: Session, payslip_id: UUID) -> list[tuple[PayslipComponent, PayComponent]]:
    return (
        db.query(PayslipComponent, PayComponent)
        .join(PayComponent, PayComponent.code == PayslipComponent.component_code)
        .filter(PayslipComponent.payslip_id == payslip_id)
        .order_by(PayslipComponent.sort_order.asc(), PayslipComponent.component_code.asc())
        .all()
    )
