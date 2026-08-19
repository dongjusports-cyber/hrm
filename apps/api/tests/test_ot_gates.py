"""Cổng OT theo mốc: 17:30 chiều · 6:00 sáng Cooker · kẹp giờ vào ca."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.modules.attendance.engine import Schedule, calculate_day

VN = timezone(timedelta(hours=7))

COOKER_FROM = time(6, 0)
COOKER_GATE = time(6, 0)


def _sched(*, holidays: set[date] | None = None) -> Schedule:
    return Schedule(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(8, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(17, 0),
        grace_late_minutes=0,
        holiday_dates=holidays or set(),
    )


def _dt(d: date, h: int, m: int = 0, s: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, s, tzinfo=VN)


def test_evening_1729_no_ot_1731_from_1700():
    d = date(2025, 10, 1)  # Wednesday — OT ngoài
    no = calculate_day([_dt(d, 8, 0), _dt(d, 17, 29)], d, _sched())
    assert no.ot_minutes == 0
    yes = calculate_day([_dt(d, 8, 0), _dt(d, 17, 31)], d, _sched())
    assert yes.ot_external_minutes == 31  # từ 17:00
    assert yes.ot_on_books_minutes == 0


def test_sunday_752_snaps_to_800_not_morning_ot():
    """1501 kiểu: CN 07:52–18:02 = 8h ×2,0 + 62p ×3,5. Không trả 7:52–8:00."""
    d = date(2026, 8, 16)
    r = calculate_day([_dt(d, 7, 52, 43), _dt(d, 18, 2, 47)], d, _sched())
    ext = r.ot_rate_minutes["external"]
    assert ext.get("2.0") == 480
    assert ext.get("3.5") == 62
    assert r.ot_external_minutes == 542
    assert r.ot_on_books_minutes == 0
    assert r.first_in.hour == 7  # vân tay giữ nguyên trên lưới


def test_cooker_before_6_gets_morning_ot():
    d = date(2025, 10, 1)
    r = calculate_day(
        [_dt(d, 5, 35), _dt(d, 17, 0)],
        d,
        _sched(),
        morning_ot_from=COOKER_FROM,
        morning_ot_qualify_before=COOKER_GATE,
    )
    assert r.ot_rate_minutes["external"].get("1.5") == 120  # 6–8
    assert r.ot_minutes == 120
    assert r.worked_hours == Decimal("8.0000")
    assert r.late_minutes == 0


def test_cooker_at_or_after_6_no_morning_ot():
    d = date(2025, 10, 1)
    at_six = calculate_day(
        [_dt(d, 6, 0), _dt(d, 17, 0)],
        d,
        _sched(),
        morning_ot_from=COOKER_FROM,
        morning_ot_qualify_before=COOKER_GATE,
    )
    after = calculate_day(
        [_dt(d, 6, 15), _dt(d, 17, 0)],
        d,
        _sched(),
        morning_ot_from=COOKER_FROM,
        morning_ot_qualify_before=COOKER_GATE,
    )
    assert at_six.ot_minutes == 0
    assert after.ot_minutes == 0


def test_cooker_sunday_before_6_from_600():
    d = date(2026, 8, 16)
    r = calculate_day(
        [_dt(d, 5, 35), _dt(d, 18, 2)],
        d,
        _sched(),
        morning_ot_from=COOKER_FROM,
        morning_ot_qualify_before=COOKER_GATE,
    )
    ext = r.ot_rate_minutes["external"]
    assert ext.get("3.5") == 120 + 62  # 6–8 + 17–18:02
    assert ext.get("2.0") == 480
    assert r.ot_type == "weekend"


def test_non_cooker_535_no_morning_ot():
    d = date(2025, 10, 1)
    r = calculate_day([_dt(d, 5, 35), _dt(d, 17, 0)], d, _sched())
    assert r.ot_minutes == 0
