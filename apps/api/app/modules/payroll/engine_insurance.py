"""
P3.4 / P6.2 — BHXH/BHYT/BHTN + công đoàn + TNCN + net (03§3.7–3.8).
Tỷ lệ / mức CD / biểu TNCN lấy từ policy — không hard-code trong công thức.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    detail: dict = field(default_factory=dict)


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

    if not inp.si_enrolled or si_base <= 0:
        bhxh = bhyt = bhtn = ZERO
    else:
        bhxh = money_vnd(si_base * rate_xh)
        bhyt = money_vnd(si_base * rate_yt)
        bhtn = money_vnd(si_base * rate_tn)

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
        detail={
            "si_base_raw": str(si_raw),
            "si_base_used": str(si_base),
            "si_base_before_cap": str(si_before_cap) if si_before_cap is not None else None,
            "si_base_cap": str(policy.get("si_base_cap")) if policy.get("si_base_cap") is not None else None,
            "taxable_income": str(taxable_income),
            "si_enrolled": inp.si_enrolled,
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
