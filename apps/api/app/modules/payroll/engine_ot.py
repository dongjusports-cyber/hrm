"""
P3.3 / 4.5 — Tiền tăng ca (22§22.8).

OT_base ≠ SI_base (policy ot_base_components / si_base_components).
Làm tròn giờ OT: theo phút (hours_step_minutes=1).
Lễ > 8h: 8 giờ × 2,0 + (giờ − 8) × 3,0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN
from typing import Any

from app.modules.payroll.component_bases import compute_si_and_ot_bases
from app.modules.payroll.engine_allowances import AllowanceLine
from app.modules.payroll.money import D, ZERO, money_vnd


@dataclass(frozen=True)
class OtHours:
    weekday: Decimal = ZERO
    weekend: Decimal = ZERO
    holiday: Decimal = ZERO
    night: Decimal = ZERO  # NT30/45/60 — tắt mặc định


@dataclass(frozen=True)
class OtInput:
    contract_salary: Decimal
    salary_divisor: Decimal
    allowance_lines: list[AllowanceLine]
    attend_full_monthly: Decimal
    hours: OtHours
    policy: dict[str, Any]


@dataclass(frozen=True)
class OtResult:
    si_contribution_base: Decimal
    ot_base: Decimal
    ot_hourly_base: Decimal
    ot_pay: Decimal
    detail: dict = field(default_factory=dict)


def quantize_ot_hours(hours: Decimal, policy: dict[str, Any]) -> Decimal:
    """22§22.8 — bậc 30 phút, floor; dưới 30 phút = 0."""
    rounding = (policy or {}).get("rounding") or {}
    step = int(rounding.get("hours_step_minutes", 30))
    if step <= 0:
        step = 30
    h = D(hours)
    if h <= 0:
        return ZERO
    minutes = h * Decimal("60")
    if minutes < step:
        return ZERO
    floored = (minutes // step) * step
    return (floored / Decimal("60")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def compute_si_contribution_base(contract_salary: Decimal, lines: list[AllowanceLine]) -> Decimal:
    """Legacy — dùng compute_si_and_ot_bases khi có policy."""
    total = D(contract_salary)
    for ln in lines:
        if ln.include_in_si_base:
            total += D(ln.monthly_full)
    return total


def compute_ot_base(
    contract_salary: Decimal,
    lines: list[AllowanceLine],
    attend_full_monthly: Decimal,
) -> tuple[Decimal, Decimal]:
    """Legacy wrapper — giữ tương thích test cũ không truyền policy."""
    si_base = compute_si_contribution_base(contract_salary, lines)
    lines_by_code = {ln.code: ln for ln in lines}
    ot_allow = ZERO
    for ln in lines:
        if not ln.include_in_ot_base:
            continue
        if ln.code == "ATTEND":
            continue
        ot_allow += D(ln.monthly_full)
    attend = D(attend_full_monthly)
    ot_base = D(contract_salary) + ot_allow + attend
    return si_base, ot_base


def _pay_bucket(
    hours: Decimal,
    hourly: Decimal,
    rate: Decimal,
    *,
    bucket_type: str,
) -> tuple[Decimal, dict | None]:
    h = D(hours)
    if h <= 0:
        return ZERO, None
    raw = h * hourly * rate
    return raw, {"type": bucket_type, "hours": str(h), "rate": str(rate), "raw": str(raw)}


def _pay_holiday(
    hours: Decimal,
    hourly: Decimal,
    rates: dict[str, Any],
) -> tuple[Decimal, list[dict]]:
    h = D(hours)
    if h <= 0:
        return ZERO, []
    rate2 = D(rates.get("holiday", "2.0"))
    rate3 = D(rates.get("holiday_over_8", "3.0"))
    parts: list[dict] = []
    if h <= Decimal("8"):
        raw = h * hourly * rate2
        parts.append({"type": "holiday", "hours": str(h), "rate": str(rate2), "raw": str(raw)})
        return raw, parts
    rest = h - Decimal("8")
    raw = Decimal("8") * hourly * rate2 + rest * hourly * rate3
    parts.append({"type": "holiday", "hours": "8", "rate": str(rate2), "raw": str(Decimal("8") * hourly * rate2)})
    parts.append(
        {
            "type": "holiday_over_8",
            "hours": str(rest),
            "rate": str(rate3),
            "raw": str(rest * hourly * rate3),
        }
    )
    return raw, parts


def compute_ot_pay(inp: OtInput) -> OtResult:
    divisor = D(inp.salary_divisor)
    if divisor <= 0:
        raise ValueError("salary_divisor phải > 0")

    policy = inp.policy or {}
    rates = policy.get("ot_rates") or {}
    night_on = bool(policy.get("ot_night_enabled", False))

    si_base, ot_base, base_detail = compute_si_and_ot_bases(
        contract_salary=inp.contract_salary,
        allowance_lines=inp.allowance_lines,
        attend_full_monthly=inp.attend_full_monthly,
        policy=policy,
    )
    hourly = ot_base / divisor / Decimal("8")

    raw_hours = {
        "weekday": D(inp.hours.weekday),
        "weekend": D(inp.hours.weekend),
        "holiday": D(inp.hours.holiday),
        "night": D(inp.hours.night),
    }
    eff_hours = {k: quantize_ot_hours(v, policy) for k, v in raw_hours.items()}

    parts: list[dict] = []
    pay = ZERO

    wk, part = _pay_bucket(
        eff_hours["weekday"],
        hourly,
        D(rates.get("weekday", "1.5")),
        bucket_type="weekday",
    )
    pay += wk
    if part:
        parts.append(part)

    we_rate = D(rates.get("weekend", rates.get("sunday", "2.0")))
    we, part = _pay_bucket(eff_hours["weekend"], hourly, we_rate, bucket_type="weekend")
    pay += we
    if part:
        parts.append(part)

    hol_raw, hol_parts = _pay_holiday(eff_hours["holiday"], hourly, rates)
    pay += hol_raw
    parts.extend(hol_parts)

    if night_on and eff_hours["night"] > 0:
        addon = D(rates.get("night_addon", "0.3"))
        h = eff_hours["night"]
        chunk = h * hourly * addon
        pay += chunk
        parts.append({"type": "night_nt", "hours": str(h), "rate": str(addon), "raw": str(chunk)})

    ot_pay = money_vnd(pay)
    return OtResult(
        si_contribution_base=si_base,
        ot_base=ot_base,
        ot_hourly_base=hourly,
        ot_pay=ot_pay,
        detail={
            **base_detail,
            "si_contribution_base": str(si_base),
            "ot_base": str(ot_base),
            "ot_hourly_base": str(hourly),
            "ot_pay": str(ot_pay),
            "raw_hours": {k: str(v) for k, v in raw_hours.items()},
            "effective_hours": {k: str(v) for k, v in eff_hours.items()},
            "parts": parts,
            "night_enabled": night_on,
            "formula": "ot_base*hours*rate/divisor/8",
        },
    )
