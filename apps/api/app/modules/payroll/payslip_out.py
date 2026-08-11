"""Map Payslip ORM → PayslipOut (dùng chung list + detail)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from app.modules.payroll.money import D
from app.modules.payroll.schemas import PayslipOut


def payslip_out(
    slip: Payslip,
    emp: Employee,
    *,
    worked_days: Decimal | None = None,
    al_days: Decimal | None = None,
    rem_days: Decimal | None = None,
    salary_divisor: Decimal | None = None,
    period: str | None = None,
    prev_net: Decimal | None = None,
) -> PayslipOut:
    net_delta = None
    if prev_net is not None:
        net_delta = D(slip.net) - D(prev_net)
    return PayslipOut(
        id=slip.id,
        pay_period_id=slip.pay_period_id,
        employee_id=slip.employee_id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        pay_channel=emp.pay_channel,
        policy_snapshot_id=slip.policy_snapshot_id,
        wd_salary=slip.wd_salary,
        allowance_total=slip.allowance_total,
        ot_pay=slip.ot_pay,
        other_adjustments=slip.other_adjustments,
        gross=slip.gross,
        taxable_income=slip.taxable_income,
        bhxh=slip.bhxh,
        bhyt=slip.bhyt,
        bhtn=slip.bhtn,
        union_fee=slip.union_fee,
        other_deductions=slip.other_deductions,
        pit_amount=slip.pit_amount,
        net=slip.net,
        status=slip.status,
        confirmed_at=slip.confirmed_at,
        confirm_deadline=slip.confirm_deadline,
        lines=slip.lines,
        worked_days=worked_days,
        al_days=al_days,
        rem_days=rem_days,
        salary_divisor=salary_divisor,
        period=period,
        prev_net=prev_net,
        net_delta=net_delta,
    )
