"""P2.3 — engine late/early/ot_minutes (pure, không DB)."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.modules.attendance.engine import Schedule, calculate_day

VN = timezone(timedelta(hours=7))


def _sched(**kwargs) -> Schedule:
    base = dict(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(8, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(17, 0),
        grace_late_minutes=0,
        holiday_dates=set(),
    )
    base.update(kwargs)
    return Schedule(**base)


def test_late_and_ot_weekday():
    # 2025-10-01 = Wednesday
    d = date(2025, 10, 1)
    punches = [
        datetime(2025, 10, 1, 8, 1, tzinfo=VN),
        datetime(2025, 10, 1, 17, 5, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.is_workday
    assert r.late_minutes == 1
    assert r.early_minutes == 0
    assert r.ot_minutes == 5
    assert r.ot_type == "weekday"
    assert r.worked_hours == Decimal("7.9833")  # khung ca tới 17:00, không cộng OT vào công


def test_early_leave():
    d = date(2025, 10, 2)  # Thursday
    punches = [
        datetime(2025, 10, 2, 8, 0, tzinfo=VN),
        datetime(2025, 10, 2, 16, 30, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.late_minutes == 0
    assert r.early_minutes == 30
    assert r.ot_minutes == 0


def test_grace_late():
    d = date(2025, 10, 3)
    punches = [datetime(2025, 10, 3, 8, 4, tzinfo=VN), datetime(2025, 10, 3, 17, 0, tzinfo=VN)]
    r = calculate_day(punches, d, _sched(grace_late_minutes=5))
    assert r.late_minutes == 0


def test_sunday_is_weekend_ot():
    d = date(2025, 10, 5)  # Sunday
    punches = [
        datetime(2025, 10, 5, 8, 0, tzinfo=VN),
        datetime(2025, 10, 5, 12, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert not r.is_workday
    assert r.ot_minutes == 240
    assert r.ot_type == "weekend"
    assert r.worked_hours == Decimal("0")
    assert r.late_minutes == 0


def test_holiday_ot():
    d = date(2025, 5, 1)
    punches = [datetime(2025, 5, 1, 9, 0, tzinfo=VN), datetime(2025, 5, 1, 11, 0, tzinfo=VN)]
    r = calculate_day(punches, d, _sched(holiday_dates={d}))
    assert r.ot_type == "holiday"
    assert r.ot_minutes == 120
