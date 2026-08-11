"""
4.3 — Tử số chia phụ cấp (22§22.3 + payload allowance_proration).

divisor = min(ngày lịch, cap) — caller truyền từ pay_period.salary_divisor.
numerator = WT + ALE + FLE + WED + HOL + COM (TMP không vào tử số).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.modules.payroll.money import D, ZERO

# COM (nghỉ bù) = mã nghỉ OFF trong hệ thống
_NUMERATOR_LEAVE: dict[str, str] = {
    "ALE": "ALE",
    "FLE": "FLE",
    "WED": "WED",
    "COM": "OFF",
}

_DEFAULT_NUMERATOR = ["WT", "ALE", "FLE", "WED", "HOL", "COM"]


def compute_numerator_days(
    *,
    worked_days: Decimal,
    leave_days_by_code: dict[str, Decimal],
    detail_days_by_category: dict[str, Decimal] | None = None,
    policy: dict[str, Any] | None = None,
) -> tuple[Decimal, dict[str, str]]:
    """Trả (tổng ngày hưởng, chi tiết từng token)."""
    proration = (policy or {}).get("allowance_proration") or {}
    tokens: list[str] = list(proration.get("numerator") or _DEFAULT_NUMERATOR)
    details = detail_days_by_category or {}
    parts: dict[str, Decimal] = {}
    total = ZERO

    for token in tokens:
        key = token.strip().upper()
        if key == "WT":
            days = D(worked_days)
        elif key == "HOL":
            days = D(details.get("HOL", ZERO))
        elif key in _NUMERATOR_LEAVE:
            code = _NUMERATOR_LEAVE[key]
            days = D(leave_days_by_code.get(code, ZERO))
        else:
            days = D(leave_days_by_code.get(key, ZERO))
        parts[key] = days
        total += days

    return total, {k: str(v) for k, v in parts.items()}


def prorate_allowance(monthly: Decimal, divisor: Decimal, numerator_days: Decimal) -> Decimal:
    if divisor <= 0:
        return ZERO
    return D(monthly) / divisor * D(numerator_days)
