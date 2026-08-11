"""
P6.2 — TNCN lũy tiến theo biểu trong Policy (không hard-code số trong caller).
Bật bằng pit_enabled=true. Mặc định tắt → pit = 0 (giữ MVP).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.modules.payroll.money import D, ZERO, money_vnd


def compute_progressive_pit(taxable: Decimal, brackets: list[Any]) -> Decimal:
    """Tính thuế lũy tiến trên thu nhập chịu thuế (đã ≥ 0)."""
    remaining = money_vnd(D(taxable))
    if remaining <= 0 or not brackets:
        return ZERO

    tax = ZERO
    prev_cap = ZERO
    for raw in brackets:
        if not isinstance(raw, dict):
            continue
        rate = D(raw.get("rate", 0))
        up_to = raw.get("up_to")
        if up_to is None:
            band_width = remaining
        else:
            cap = D(up_to)
            band_width = cap - prev_cap
            if band_width < 0:
                band_width = ZERO
            prev_cap = cap
        slice_amt = remaining if up_to is None else min(remaining, band_width)
        if slice_amt > 0 and rate > 0:
            tax += slice_amt * rate
            remaining -= slice_amt
        if remaining <= 0:
            break
    return money_vnd(tax)


def compute_pit_amount(
    *,
    gross: Decimal,
    bhxh: Decimal,
    bhyt: Decimal,
    bhtn: Decimal,
    tax_dependent_count: int,
    pit_enrolled: bool,
    policy: dict[str, Any],
) -> tuple[Decimal, dict[str, Any]]:
    """
    taxable = max(0, gross - BH bắt buộc - giảm trừ bản thân - NPT × giảm trừ NPT)
    pit = progressive(taxable) khi pit_enabled và pit_enrolled.
    """
    policy = policy or {}
    enabled = bool(policy.get("pit_enabled", False))
    detail: dict[str, Any] = {
        "pit_enabled": enabled,
        "pit_enrolled": pit_enrolled,
        "tax_dependent_count": int(tax_dependent_count or 0),
    }
    if not enabled or not pit_enrolled:
        detail["pit_amount"] = "0"
        detail["reason"] = "disabled" if not enabled else "not_enrolled"
        return ZERO, detail

    personal = money_vnd(D(policy.get("pit_personal_deduction", 0)))
    per_dep = money_vnd(D(policy.get("pit_dependent_deduction", 0)))
    deps = max(0, int(tax_dependent_count or 0))
    assessable = money_vnd(D(gross) - D(bhxh) - D(bhyt) - D(bhtn))
    taxable = money_vnd(assessable - personal - per_dep * Decimal(deps))
    if taxable < 0:
        taxable = ZERO

    brackets = policy.get("pit_brackets") or []
    if not isinstance(brackets, list):
        brackets = []
    pit = compute_progressive_pit(taxable, brackets)
    detail.update(
        {
            "assessable": str(assessable),
            "personal_deduction": str(personal),
            "dependent_deduction_total": str(money_vnd(per_dep * Decimal(deps))),
            "taxable": str(taxable),
            "pit_amount": str(pit),
        }
    )
    return pit, detail
