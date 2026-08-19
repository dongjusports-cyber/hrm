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
    # 2025-10-01 = Wednesday — OT ngoài sau 17:30
    d = date(2025, 10, 1)
    punches = [
        datetime(2025, 10, 1, 8, 1, tzinfo=VN),
        datetime(2025, 10, 1, 17, 5, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.is_workday
    assert r.late_minutes == 1
    assert r.early_minutes == 0
    assert r.ot_minutes == 0  # 17:05 trong nghỉ cơm 17:00–17:30
    assert r.ot_on_books_minutes == 0
    assert r.ot_external_minutes == 0
    assert r.worked_hours == Decimal("7.9833")


def test_ot_starts_after_dinner_1730():
    d = date(2025, 10, 1)  # Wednesday
    punches = [
        datetime(2025, 10, 1, 8, 0, tzinfo=VN),
        datetime(2025, 10, 1, 17, 20, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.ot_minutes == 0  # nghỉ cơm, không OT


def test_ot_from_1700_when_out_after_dinner():
    d = date(2025, 10, 1)  # Wednesday
    punches = [
        datetime(2025, 10, 1, 8, 0, tzinfo=VN),
        datetime(2025, 10, 1, 18, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.ot_minutes == 60  # từ 17:00
    assert r.ot_external_minutes == 60


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
    assert r.ot_external_minutes == 240
    assert r.ot_on_books_minutes == 0
    assert r.worked_hours == Decimal("0")
    assert r.late_minutes == 0


def test_sunday_full_day_excludes_lunch():
    """CN 08:00–17:00 = 8 giờ OT (trừ 12:00–13:00), không phải 9 giờ."""
    d = date(2025, 10, 5)
    punches = [
        datetime(2025, 10, 5, 8, 0, tzinfo=VN),
        datetime(2025, 10, 5, 17, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.ot_type == "weekend"
    assert r.ot_minutes == 480
    assert r.ot_external_minutes == 480


def test_sunday_morning_only_no_lunch_to_subtract():
    d = date(2025, 10, 5)
    punches = [
        datetime(2025, 10, 5, 8, 0, tzinfo=VN),
        datetime(2025, 10, 5, 11, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.ot_minutes == 180


def test_holiday_ot():
    d = date(2025, 5, 1)
    punches = [datetime(2025, 5, 1, 9, 0, tzinfo=VN), datetime(2025, 5, 1, 11, 0, tzinfo=VN)]
    r = calculate_day(punches, d, _sched(holiday_dates={d}))
    assert r.ot_type == "holiday"
    assert r.ot_minutes == 120
    assert r.ot_external_minutes == 120
    assert r.ot_on_books_minutes == 0


def test_holiday_full_day_excludes_lunch():
    d = date(2025, 5, 1)
    punches = [
        datetime(2025, 5, 1, 8, 0, tzinfo=VN),
        datetime(2025, 5, 1, 17, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(holiday_dates={d}))
    assert r.ot_type == "holiday"
    assert r.ot_minutes == 480


def test_single_punch_out_only_records_last_out():
    """Chỉ bấm giờ về — ghi nhận giờ ra, HR/AI rà soát thiếu vào."""
    d = date(2026, 8, 7)  # Friday
    punches = [datetime(2026, 8, 7, 17, 8, tzinfo=VN)]
    r = calculate_day(punches, d, _sched())
    assert r.punch_count == 1
    assert r.first_in is None
    assert r.last_out == punches[0]
    assert r.late_minutes == 0
    assert r.early_minutes == 0
    assert r.ot_minutes == 0  # nghỉ cơm 17:00–17:30
    assert r.worked_hours == Decimal("0")


def test_single_punch_in_only_records_first_in():
    d = date(2026, 8, 8)  # Saturday workday in sched
    punches = [datetime(2026, 8, 8, 8, 5, tzinfo=VN)]
    r = calculate_day(punches, d, _sched())
    assert r.punch_count == 1
    assert r.first_in == punches[0]
    assert r.last_out is None
    assert r.late_minutes == 5
    assert r.ot_minutes == 0


def test_afternoon_only_pair_half_day_and_late():
    """Nghỉ sáng, bấm 12:30 + 17:07 — công 4h (0.5 ngày), ghi nhận đi trễ."""
    d = date(2026, 8, 15)
    punches = [
        datetime(2026, 8, 15, 12, 30, 0, tzinfo=VN),
        datetime(2026, 8, 15, 17, 7, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.first_in == punches[0]
    assert r.last_out == punches[1]
    assert r.punch_count == 2
    assert r.worked_hours == Decimal("4.0000")
    assert r.late_minutes == 270
    assert r.early_minutes == 0


def test_lunch_in_1214_and_out_1710():
    """HR/máy 12:14 + chiều 17:10 — phải giữ cả vào và ra, không nuốt 17:10 (nghỉ cơm)."""
    d = date(2026, 8, 17)  # Monday
    punches = [
        datetime(2026, 8, 17, 12, 14, 0, tzinfo=VN),
        datetime(2026, 8, 17, 17, 10, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.first_in == punches[0]
    assert r.last_out == punches[1]
    assert r.punch_count == 2
    assert r.worked_hours == Decimal("4.0000")
    assert r.late_minutes == 254
    assert r.early_minutes == 0
    assert r.ot_minutes == 0


def test_two_close_afternoon_exits_stay_out_only():
    """Hai lần bấm ra gần nhau — không bị biến thành vào+ra."""
    d = date(2026, 8, 15)
    punches = [
        datetime(2026, 8, 15, 17, 7, 0, tzinfo=VN),
        datetime(2026, 8, 15, 17, 10, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.first_in is None
    assert r.last_out == punches[1]
    assert r.worked_hours == Decimal("0")


def test_double_tap_deduped_to_single_out():
    d = date(2026, 8, 7)
    punches = [
        datetime(2026, 8, 7, 17, 8, 0, tzinfo=VN),
        datetime(2026, 8, 7, 17, 8, 30, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.punch_count == 1
    assert r.first_in is None
    assert r.last_out == punches[0]
    assert r.ot_minutes == 0
