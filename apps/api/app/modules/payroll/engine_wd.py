"""
P3.1 — Lương ngày công (wd_salary).

WD = Lương HĐ (hoặc thử việc) / salary_divisor × (worked + AL)  (10§#5)
Thử việc theo ngày ký HĐ; AL tính theo mức HĐ.
Không hard-code divisor — caller truyền từ pay_period / calendar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.modules.payroll.money import D, ZERO, money_vnd


@dataclass(frozen=True)
class WdSalaryInput:
    contract_salary: Decimal
    probation_salary: Decimal
    salary_divisor: Decimal
    worked_days: Decimal
    al_days: Decimal  # chỉ tham chiếu tổng hợp — không cộng vào wd_salary (4.2)
    period_from: date
    period_to: date
    contract_signed_at: date | None
    work_weekdays: tuple[int, ...]
    holiday_dates: frozenset[date]
    sal_allow: Decimal = ZERO


@dataclass(frozen=True)
class WdSalaryResult:
    wd_salary: Decimal
    official_amount: Decimal
    probation_amount: Decimal
    contract_days: Decimal
    probation_days: Decimal
    al_days: Decimal
    paid_days: Decimal
    salary_divisor: Decimal
    sal_allow: Decimal
    detail: dict


def _is_workday(d: date, work_weekdays: tuple[int, ...], holidays: frozenset[date]) -> bool:
    if d in holidays:
        return False
    return d.isoweekday() in work_weekdays


def count_workdays(start: date, end: date, work_weekdays: tuple[int, ...], holidays: frozenset[date]) -> int:
    if end < start:
        return 0
    n = 0
    cur = start
    while cur <= end:
        if _is_workday(cur, work_weekdays, holidays):
            n += 1
        cur += timedelta(days=1)
    return n


def split_days_by_contract(days: Decimal, inp: WdSalaryInput) -> tuple[Decimal, Decimal]:
    """Chia số ngày (công hoặc nghỉ) → (official, probation) — 22§22.4."""
    fake = WdSalaryInput(
        contract_salary=inp.contract_salary,
        probation_salary=inp.probation_salary,
        salary_divisor=inp.salary_divisor,
        worked_days=days,
        al_days=ZERO,
        period_from=inp.period_from,
        period_to=inp.period_to,
        contract_signed_at=inp.contract_signed_at,
        work_weekdays=inp.work_weekdays,
        holiday_dates=inp.holiday_dates,
        sal_allow=inp.sal_allow,
    )
    return split_worked_by_contract(fake)


def split_worked_by_contract(inp: WdSalaryInput) -> tuple[Decimal, Decimal]:
    """Tách worked_days → (contract_days, probation_days)."""
    worked = D(inp.worked_days)
    if worked < 0:
        worked = ZERO
    signed = inp.contract_signed_at
    if signed is None or signed > inp.period_to:
        return ZERO, worked
    if signed <= inp.period_from:
        return worked, ZERO

    # Ký HĐ giữa tháng: chia theo tỉ lệ ngày công chuẩn trước/sau ngày ký
    before = count_workdays(
        inp.period_from, signed - timedelta(days=1), inp.work_weekdays, inp.holiday_dates
    )
    after = count_workdays(signed, inp.period_to, inp.work_weekdays, inp.holiday_dates)
    total = before + after
    if total == 0:
        return worked, ZERO
    probation = (worked * Decimal(before) / Decimal(total)).quantize(Decimal("0.0001"))
    contract = worked - probation
    return contract, probation


def compute_wd_salary(inp: WdSalaryInput) -> WdSalaryResult:
    divisor = D(inp.salary_divisor)
    if divisor <= 0:
        raise ValueError("salary_divisor phải > 0")

    sal = D(inp.sal_allow)
    contract_days, probation_days = split_worked_by_contract(inp)
    al_days = max(D(inp.al_days), ZERO)
    official_rate = (D(inp.contract_salary) + sal) / divisor
    probation_rate = (D(inp.probation_salary) + sal) / divisor
    official_part = official_rate * contract_days
    probation_part = probation_rate * probation_days
    raw = official_part + probation_part
    wd = money_vnd(raw)
    official_amt = money_vnd(official_part)
    probation_amt = money_vnd(probation_part)
    paid_days = contract_days + probation_days + al_days

    return WdSalaryResult(
        wd_salary=wd,
        official_amount=official_amt,
        probation_amount=probation_amt,
        contract_days=contract_days,
        probation_days=probation_days,
        al_days=al_days,
        paid_days=paid_days,
        salary_divisor=divisor,
        sal_allow=sal,
        detail={
            "formula": "(basic+sal_allow)/divisor*official_days + (prob+sal_allow)/divisor*probation_days",
            "contract_salary": str(D(inp.contract_salary)),
            "probation_salary": str(D(inp.probation_salary)),
            "sal_allow": str(sal),
            "salary_divisor": str(divisor),
            "worked_days": str(D(inp.worked_days)),
            "contract_days": str(contract_days),
            "probation_days": str(probation_days),
            "al_days": str(al_days),
            "official_amount": str(official_amt),
            "probation_amount": str(probation_amt),
            "raw_before_round": str(raw),
            "wd_salary": str(wd),
            "note": "AL tính ở lương ngày nghỉ (engine_leave_pay), không gộp vào WD.",
        },
    )
