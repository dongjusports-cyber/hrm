"""
P3.4 / P6.2 — BHXH/BHYT/BHTN + công đoàn + TNCN + net (03§3.7–3.8).
Tỷ lệ / mức CD / biểu TNCN lấy từ policy — không hard-code trong công thức.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.modules.payroll.component_bases import apply_si_base_cap
from app.modules.payroll.engine_pit import compute_pit_amount
from app.modules.payroll.money import D, ZERO, money_vnd


@dataclass(frozen=True)
class InsuranceInput:
    si_contribution_base: Decimal
    si_enrolled: bool
    si_base_override: Decimal | None
    union_fee_override: Decimal | None
    gross: Decimal
    other_deductions: Decimal
    other_adjustments: Decimal  # đã nằm trong gross nếu caller cộng; giữ để ghi detail
    policy: dict[str, Any]
    tax_dependent_count: int = 0
    pit_enrolled: bool = True
    worked_days: Decimal | None = None
    resign_date: date | None = None
    period_start: date | None = None


@dataclass(frozen=True)
class InsuranceResult:
    si_base_used: Decimal
    si_base_raw: Decimal
    taxable_income: Decimal
    bhxh: Decimal
    bhyt: Decimal
    bhtn: Decimal
    union_fee: Decimal
    other_deductions: Decimal
    pit_amount: Decimal
    net: Decimal
    si_charged: bool = False
    si_base_charged: Decimal = ZERO
    detail: dict = field(default_factory=dict)


def si_month_eligible(
    *,
    si_enrolled: bool,
    worked_days: Decimal | None,
    resign_date: date | None,
    period_start: date | None,
    policy: dict[str, Any],
) -> bool:
    """CTY: tick BHXH + ≥ 12 ngày công WT + còn làm từ ngày 16 (thôi việc 15 → không đóng)."""
    if not si_enrolled:
        return False
    if period_start is None:
        return True
    rule = (policy or {}).get("si_month_rule") or {}
    min_days = D(rule.get("min_worked_days", 12))
    from_day = int(rule.get("from_day_of_month", 16) or 16)
    if D(worked_days or 0) < min_days:
        return False
    cutoff = date(period_start.year, period_start.month, from_day)
    if resign_date is not None and resign_date < cutoff:
        return False
    return True


def compute_insurance_and_net(inp: InsuranceInput) -> InsuranceResult:
    policy = inp.policy or {}
    rates = policy.get("si_rates") or {}
    rate_xh = D(rates.get("bhxh", "0.08"))
    rate_yt = D(rates.get("bhyt", "0.015"))
    rate_tn = D(rates.get("bhtn", "0.01"))

    if inp.si_base_override is not None:
        si_raw = D(inp.si_base_override)
    else:
        si_raw = D(inp.si_contribution_base)

    si_base, si_before_cap = apply_si_base_cap(si_raw, policy)
    charged = si_month_eligible(
        si_enrolled=inp.si_enrolled,
        worked_days=inp.worked_days,
        resign_date=inp.resign_date,
        period_start=inp.period_start,
        policy=policy,
    )

    if not charged or si_base <= 0:
        bhxh = bhyt = bhtn = ZERO
        union = ZERO
        si_base_charged = ZERO
    else:
        bhxh = money_vnd(si_base * rate_xh)
        bhyt = money_vnd(si_base * rate_yt)
        bhtn = money_vnd(si_base * rate_tn)
        si_base_charged = si_base
        if inp.union_fee_override is not None:
            union = money_vnd(D(inp.union_fee_override))
        else:
            union = money_vnd(D(policy.get("union_fee_default", 0)))

    other_ded = money_vnd(D(inp.other_deductions))
    gross = money_vnd(D(inp.gross))
    taxable_income = money_vnd(gross - bhxh - bhyt - bhtn)
    if taxable_income < 0:
        taxable_income = ZERO

    pit, pit_detail = compute_pit_amount(
        gross=gross,
        bhxh=bhxh,
        bhyt=bhyt,
        bhtn=bhtn,
        tax_dependent_count=inp.tax_dependent_count,
        pit_enrolled=inp.pit_enrolled,
        policy=policy,
    )
    net = money_vnd(gross - bhxh - bhyt - bhtn - union - other_ded - pit)

    return InsuranceResult(
        si_base_used=si_base,
        si_base_raw=si_raw,
        taxable_income=taxable_income,
        bhxh=bhxh,
        bhyt=bhyt,
        bhtn=bhtn,
        union_fee=union,
        other_deductions=other_ded,
        pit_amount=pit,
        net=net,
        si_charged=charged and si_base > 0,
        si_base_charged=si_base_charged,
        detail={
            "si_base_raw": str(si_raw),
            "si_base_used": str(si_base),
            "si_base_charged": str(si_base_charged),
            "si_charged": charged and si_base > 0,
            "si_base_before_cap": str(si_before_cap) if si_before_cap is not None else None,
            "si_base_cap": str(policy.get("si_base_cap")) if policy.get("si_base_cap") is not None else None,
            "taxable_income": str(taxable_income),
            "si_enrolled": inp.si_enrolled,
            "worked_days": str(D(inp.worked_days)) if inp.worked_days is not None else None,
            "resign_date": inp.resign_date.isoformat() if inp.resign_date else None,
            "rates": {"bhxh": str(rate_xh), "bhyt": str(rate_yt), "bhtn": str(rate_tn)},
            "bhxh": str(bhxh),
            "bhyt": str(bhyt),
            "bhtn": str(bhtn),
            "union_fee": str(union),
            "other_deductions": str(other_ded),
            "pit": pit_detail,
            "pit_amount": str(pit),
            "gross": str(gross),
            "net": str(net),
            "formula": "taxable_income=gross-bhxh-bhyt-bhtn; net=gross-all_deductions",
        },
    )
