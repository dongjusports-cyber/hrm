"""OT Dongju — cắt phút theo khung giờ / 8 hệ số."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.modules.attendance.engine import Schedule, calculate_day
from app.modules.attendance.ot_bands import add_interval_minutes, rate_for_datetime

VN = timezone(timedelta(hours=7))


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


def _dt(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m, tzinfo=VN)


def test_rate_weekday_evening_and_night():
    d = date(2026, 8, 19)  # Wednesday
    assert rate_for_datetime(_dt(d, 18, 0), set()) == Decimal("1.5")
    assert rate_for_datetime(_dt(d, 23, 0), set()) == Decimal("2.1")
    assert rate_for_datetime(_dt(d, 5, 0), set()) == Decimal("2.1")
    assert rate_for_datetime(_dt(d, 7, 0), set()) == Decimal("1.5")
    assert rate_for_datetime(_dt(d, 10, 0), set()) == Decimal("0")


def test_rate_sunday_and_holiday():
    sun = date(2026, 8, 23)
    hol = date(2026, 9, 2)
    holidays = {hol}
    assert rate_for_datetime(_dt(sun, 10, 0), holidays) == Decimal("2.0")
    assert rate_for_datetime(_dt(sun, 18, 0), holidays) == Decimal("3.5")
    assert rate_for_datetime(_dt(sun, 23, 0), holidays) == Decimal("4.1")
    assert rate_for_datetime(_dt(hol, 10, 0), holidays) == Decimal("3.0")
    assert rate_for_datetime(_dt(hol, 18, 0), holidays) == Decimal("4.5")
    assert rate_for_datetime(_dt(hol, 23, 0), holidays) == Decimal("5.1")


def test_midnight_split_sunday_to_monday():
    """CN 22h–0h = 4,1 · T2 0h–6h = 2,1."""
    sun = date(2026, 8, 23)
    mon = date(2026, 8, 24)
    dest: dict[str, int] = {}
    add_interval_minutes(
        dest,
        _dt(sun, 22, 0),
        _dt(mon, 6, 0),
        set(),
        skip_lunch=False,
    )
    assert dest["4.1"] == 120
    assert dest["2.1"] == 360


def test_engine_weekday_evening_150():
    d = date(2025, 10, 1)  # Wednesday — OT ngoài
    r = calculate_day([_dt(d, 8, 0), _dt(d, 18, 0)], d, _sched())
    assert r.ot_minutes == 60
    assert r.ot_rate_minutes["external"].get("1.5") == 60
    assert r.ot_on_books_minutes == 0


def test_engine_tuesday_on_books_until_20():
    d = date(2025, 10, 7)  # Tuesday T3
    r = calculate_day([_dt(d, 8, 0), _dt(d, 21, 0)], d, _sched())
    assert r.ot_on_books_minutes == 180  # 17–20
    assert r.ot_external_minutes == 60  # 20–21
    assert r.ot_rate_minutes["on_books"].get("1.5") == 180
    assert r.ot_rate_minutes["external"].get("1.5") == 60


def test_engine_weekday_night_210():
    d = date(2025, 10, 1)
    r = calculate_day([_dt(d, 8, 0), _dt(d, 23, 0)], d, _sched())
    assert r.ot_rate_minutes["external"].get("1.5") == 300  # 17–22
    assert r.ot_rate_minutes["external"].get("2.1") == 60  # 22–23


def test_engine_sunday_core_200_minus_lunch():
    d = date(2025, 10, 5)  # Sunday
    r = calculate_day([_dt(d, 8, 0), _dt(d, 17, 0)], d, _sched())
    assert r.is_workday is False
    assert r.ot_type == "weekend"
    assert r.ot_rate_minutes["external"].get("2.0") == 480  # 8h trừ cơm
    assert r.ot_minutes == 480


def test_engine_saturday_same_as_weekday():
    d = date(2025, 10, 4)  # Saturday
    r = calculate_day([_dt(d, 8, 0), _dt(d, 23, 0)], d, _sched())
    assert r.is_workday is True
    assert r.ot_rate_minutes["external"].get("1.5") == 300  # 17–22
    assert r.ot_rate_minutes["external"].get("2.1") == 60  # 22–23
    assert "2.0" not in (r.ot_rate_minutes["external"] or {})


def test_engine_holiday_evening_450():
    d = date(2025, 10, 10)
    r = calculate_day(
        [_dt(d, 8, 0), _dt(d, 22, 0)],
        d,
        _sched(holidays={d}),
    )
    assert r.ot_type == "holiday"
    assert r.ot_rate_minutes["external"].get("3.0") == 480
    assert r.ot_rate_minutes["external"].get("4.5") == 300  # 17–22
