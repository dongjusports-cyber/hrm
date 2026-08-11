"""
CalendarEngine — đếm official_work_days + áp divisor_rule từ Policy (không hard-code 26).
"""

from __future__ import annotations

import calendar as py_calendar
from datetime import date
from decimal import Decimal
from typing import Any


def count_official_work_days(
    *,
    year: int,
    month: int,
    work_weekdays: list[int],
    holiday_dates: set[date],
) -> Decimal:
    """
    work_weekdays: 1=Mon .. 7=Sun (ISO).
    Ngày lễ trùng ngày làm việc thì trừ.
    """
    if month < 1 or month > 12:
        raise ValueError("Tháng không hợp lệ.")
    days_in_month = py_calendar.monthrange(year, month)[1]
    work_set = set(work_weekdays)
    total = 0
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        iso = d.isoweekday()  # 1=Mon .. 7=Sun
        if iso not in work_set:
            continue
        if d in holiday_dates:
            continue
        total += 1
    return Decimal(total)


def apply_divisor_rule(official_work_days: Decimal, rule: dict[str, Any] | None) -> Decimal:
    """
    22§22.12: min(ngày lịch, cap) khi source=calendar_working_days.
    Legacy: IF official == 27 → 26 ELSE official.
    """
    if not rule:
        rule = {"when_official_eq": 27, "use_divisor": 26, "else": "official"}

    if rule.get("source") == "calendar_working_days" and rule.get("cap") is not None:
        cap = Decimal(str(rule["cap"]))
        return min(official_work_days, cap)

    when_eq = Decimal(str(rule.get("when_official_eq", 27)))
    use_div = Decimal(str(rule.get("use_divisor", 26)))
    else_mode = rule.get("else", "official")

    if official_work_days == when_eq:
        return use_div
    if else_mode == "official":
        return official_work_days
    return Decimal(str(else_mode))
