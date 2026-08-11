"""Quy tắc tiền — Decimal, chỉ tròn đồng ở bước cuối (13§13.1)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

VND = Decimal("1")
ZERO = Decimal("0")


def D(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money_vnd(amount: Decimal) -> Decimal:
    """Làm tròn đồng (HALF_UP)."""
    return D(amount).quantize(VND, rounding=ROUND_HALF_UP)
