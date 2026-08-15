"""Bước C — chuyển WorkShift (ca của Tổ) thành Schedule cho engine.

KHÔNG viết resolver mới: shift_id đã được day_enrich.build_shift_cache /
resolve_work_shift_id lấy sẵn. File này chỉ ánh xạ WorkShift → Schedule và
tách mốc OT (ot_start) khỏi mốc hết ca (end_time) — xem 22§22.13.

`ot_start`/`end_time` bằng nhau ở ca ADMIN nhưng khác nhau ở ca CLEANER
(hết ca 16:00, OT bắt đầu 17:00). Không suy mốc OT từ giờ hết ca.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from app.modules.attendance.engine import Schedule
from app.modules.attendance.models import WorkShift


@dataclass(frozen=True)
class ShiftTiming:
    schedule: Schedule  # dùng cho calculate_day
    ot_start_time: time  # mốc bắt đầu OT ngày thường (tách khỏi end_time)
    standard_hours: Decimal


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
    return ShiftTiming(schedule=schedule, ot_start_time=ot_start_time, standard_hours=standard_hours)
