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
    by_rate: dict[str, Decimal] = field(default_factory=dict)


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


@dataclass(frozen=True)
class OtRateBuckets:
    """Giờ + tiền theo 8 hệ số khung giờ công ty."""

    hours_x15: Decimal = ZERO
    pay_x15: Decimal = ZERO
    hours_x21: Decimal = ZERO
    pay_x21: Decimal = ZERO
    hours_x20: Decimal = ZERO
    pay_x20: Decimal = ZERO
    hours_x35: Decimal = ZERO
    pay_x35: Decimal = ZERO
    hours_x41: Decimal = ZERO
    pay_x41: Decimal = ZERO
    hours_x30: Decimal = ZERO
    pay_x30: Decimal = ZERO
    hours_x45: Decimal = ZERO
    pay_x45: Decimal = ZERO
    hours_x51: Decimal = ZERO
    pay_x51: Decimal = ZERO

    def plus(self, other: "OtRateBuckets") -> "OtRateBuckets":
        return OtRateBuckets(
            hours_x15=self.hours_x15 + other.hours_x15,
            pay_x15=self.pay_x15 + other.pay_x15,
            hours_x21=self.hours_x21 + other.hours_x21,
            pay_x21=self.pay_x21 + other.pay_x21,
            hours_x20=self.hours_x20 + other.hours_x20,
            pay_x20=self.pay_x20 + other.pay_x20,
            hours_x35=self.hours_x35 + other.hours_x35,
            pay_x35=self.pay_x35 + other.pay_x35,
            hours_x41=self.hours_x41 + other.hours_x41,
            pay_x41=self.pay_x41 + other.pay_x41,
            hours_x30=self.hours_x30 + other.hours_x30,
            pay_x30=self.pay_x30 + other.pay_x30,
            hours_x45=self.hours_x45 + other.hours_x45,
            pay_x45=self.pay_x45 + other.pay_x45,
            hours_x51=self.hours_x51 + other.hours_x51,
            pay_x51=self.pay_x51 + other.pay_x51,
        )


_RATE_FIELDS = (
    ("1.5", "hours_x15", "pay_x15"),
    ("2.1", "hours_x21", "pay_x21"),
    ("2.0", "hours_x20", "pay_x20"),
    ("3.5", "hours_x35", "pay_x35"),
    ("4.1", "hours_x41", "pay_x41"),
    ("3.0", "hours_x30", "pay_x30"),
    ("4.5", "hours_x45", "pay_x45"),
    ("5.1", "hours_x51", "pay_x51"),
)


def buckets_from_parts(parts: list[dict] | None) -> OtRateBuckets:
    """Gom parts compute_ot_pay → 8 cột hệ số."""
    hours: dict[str, Decimal] = {k: ZERO for k, _, _ in _RATE_FIELDS}
    pay: dict[str, Decimal] = {k: ZERO for k, _, _ in _RATE_FIELDS}
    for part in parts or []:
        rate_key = f"{D(part.get('rate', 0)):.1f}"
        kind = str(part.get("type") or "")
        h = D(part.get("hours", 0))
        raw = D(part.get("raw", 0))
        if rate_key not in hours:
            if kind == "weekday":
                rate_key = "1.5"
            elif kind in ("weekend",):
                rate_key = "2.0"
            elif kind == "holiday":
                rate_key = "2.0"
            elif kind == "holiday_over_8":
                rate_key = "3.0"
            else:
                continue
        hours[rate_key] = hours.get(rate_key, ZERO) + h
        pay[rate_key] = pay.get(rate_key, ZERO) + raw
    kwargs = {}
    for key, hf, pf in _RATE_FIELDS:
        kwargs[hf] = hours.get(key, ZERO)
        kwargs[pf] = money_vnd(pay.get(key, ZERO))
    return OtRateBuckets(**kwargs)


def buckets_from_hours_map(
    hours_map: dict[str, Decimal] | None,
    hourly: Decimal,
) -> OtRateBuckets:
    """Giờ theo hệ số × đơn giá/giờ → tiền từng mốc (chưa làm tròn giờ)."""
    kwargs: dict[str, Decimal] = {}
    for key, hf, pf in _RATE_FIELDS:
        h = D((hours_map or {}).get(key, 0))
        kwargs[hf] = h
        kwargs[pf] = money_vnd(h * hourly * D(key)) if h > 0 else ZERO
    return OtRateBuckets(**kwargs)


def hours_map_from_timesheet(ts: Any, channel: str) -> dict[str, Decimal]:
    raw = getattr(ts, "ot_hours_by_rate", None) or {}
    if not isinstance(raw, dict):
        return {}
    block = raw.get(channel) or {}
    if not isinstance(block, dict):
        return {}
    return {str(k): D(v) for k, v in block.items() if D(v) > 0}


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

    by_rate = {str(k): D(v) for k, v in (inp.hours.by_rate or {}).items() if D(v) > 0}
    if by_rate:
        parts: list[dict] = []
        pay = ZERO
        eff_hours = {k: quantize_ot_hours(v, policy) for k, v in by_rate.items()}
        for key in sorted(eff_hours, key=lambda k: D(k)):
            hours = eff_hours[key]
            chunk, part = _pay_bucket(hours, hourly, D(key), bucket_type=f"x{key}")
            pay += chunk
            if part:
                parts.append(part)
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
                "raw_hours": {k: str(v) for k, v in by_rate.items()},
                "effective_hours": {k: str(v) for k, v in eff_hours.items()},
                "parts": parts,
                "night_enabled": bool(policy.get("ot_night_enabled", False)),
                "formula": "ot_base*hours*rate/divisor/8",
                "time_bands": True,
            },
        )

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
