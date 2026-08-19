"""Bước C — chuyển WorkShift (ca của Tổ) thành Schedule cho engine.

KHÔNG viết resolver mới: shift_id đã được day_enrich.build_shift_cache /
resolve_work_shift_id lấy sẵn. File này chỉ ánh xạ WorkShift → Schedule và
tách mốc OT (ot_start) khỏi mốc hết ca (end_time) — xem 22§22.13.

`ot_start`/`end_time` bằng nhau ở ca ADMIN nhưng khác nhau ở ca CLEANER
(hết ca 16:00, OT bắt đầu 17:00). Không suy mốc OT từ giờ hết ca.
COOKER: cổng OT sáng — Luật/02-OT.md · Luật/07-CA-CHE-DO.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from app.modules.attendance.engine import Schedule
from app.modules.attendance.models import WorkShift
from app.modules.attendance.seed_shifts import COOKER_SHIFT_CODE


@dataclass(frozen=True)
class ShiftTiming:
    schedule: Schedule  # dùng cho calculate_day
    ot_start_time: time  # mốc bắt đầu OT ngày thường (tách khỏi end_time)
    standard_hours: Decimal
    morning_ot_from: time | None = None
    morning_ot_qualify_before: time | None = None


def engine_ot_kwargs(timing: ShiftTiming) -> dict:
    """Tham số OT truyền vào calculate_day (chiều + cổng sáng Cooker)."""
    return {
        "ot_start": timing.ot_start_time,
        "standard_hours": timing.standard_hours,
        "morning_ot_from": timing.morning_ot_from,
        "morning_ot_qualify_before": timing.morning_ot_qualify_before,
    }


def timing_from_shift(shift: WorkShift | None, company: Schedule) -> ShiftTiming:
    """None → trả nguyên lịch công ty (hồi quy 100%).

    Giữ grace (trễ/sớm) và danh sách ngày làm việc / lễ theo lịch công ty —
    grace không theo ca. Chỉ khung giờ ca (vào/trưa/hết ca) lấy từ WorkShift.
    """
    if shift is None:
        return ShiftTiming(
            schedule=company,
            ot_start_time=company.afternoon_end,
            standard_hours=Decimal("8"),
        )

    schedule = Schedule(
        work_weekdays=company.work_weekdays,
        morning_start=shift.start_time,
        morning_end=shift.lunch_start or company.morning_end,
        afternoon_start=shift.lunch_end or company.afternoon_start,
        afternoon_end=shift.end_time,
        grace_late_minutes=company.grace_late_minutes,
        holiday_dates=company.holiday_dates,
        grace_late_seconds=company.grace_late_seconds,
        grace_early_seconds=company.grace_early_seconds,
    )
    ot_start_time = shift.ot_start or shift.end_time
    standard_hours = shift.standard_hours or Decimal("8")
    morning_from = morning_gate = None
    if shift.code == COOKER_SHIFT_CODE:
        morning_from = time(6, 0)
        morning_gate = time(6, 0)
    return ShiftTiming(
        schedule=schedule,
        ot_start_time=ot_start_time,
        standard_hours=standard_hours,
        morning_ot_from=morning_from,
        morning_ot_qualify_before=morning_gate,
    )
