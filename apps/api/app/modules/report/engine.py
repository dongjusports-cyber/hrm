"""Công thức KPI — HIEN_PHAP 04§4.6 (Attendance 2026). Pure Decimal, không I/O."""

from __future__ import annotations

from decimal import Decimal

from app.modules.payroll.money import D, ZERO, money_vnd


def monthly_manpower(headcount: int, param_b3: Decimal) -> Decimal:
    return D(headcount) * D(param_b3)


def attendance_rate(attendants: Decimal, manpower: Decimal) -> Decimal | None:
    if manpower <= 0:
        return None
    return (D(attendants) / D(manpower)).quantize(Decimal("0.0001"))


def end_headcount(begin_hc: int, recruit: int, resign: int) -> int:
    return begin_hc + recruit - resign


def turnover_rate(resign: int, begin_hc: int, end_hc: int) -> Decimal | None:
    avg = (D(begin_hc) + D(end_hc)) / D(2)
    if avg <= 0:
        return None
    return (D(resign) / avg).quantize(Decimal("0.0001"))


def ot_rate(ot_hours: Decimal, reference_hours: Decimal) -> Decimal | None:
    if reference_hours <= 0:
        return None
    return (D(ot_hours) / D(reference_hours)).quantize(Decimal("0.0001"))


def reference_hours(headcount: int, work_days: Decimal, hours_per_day: Decimal) -> Decimal:
    return D(headcount) * D(work_days) * D(hours_per_day)


def pct(rate: Decimal | None) -> Decimal | None:
    if rate is None:
        return None
    return (rate * D(100)).quantize(Decimal("0.01"))


def money_sum(values: list[Decimal]) -> Decimal:
    total = ZERO
    for v in values:
        total += D(v)
    return money_vnd(total)
