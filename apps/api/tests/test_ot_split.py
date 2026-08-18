"""Tách OT sổ / OT ngoài — engine + policy."""

from datetime import date, datetime, time, timedelta, timezone

from app.modules.attendance.engine import Schedule, calculate_day
from app.modules.attendance.ot_split import OtSplitPolicy, split_weekday_ot_minutes

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


def _policy() -> OtSplitPolicy:
    return OtSplitPolicy(
        on_books_weekdays=frozenset({2, 4}),
        on_books_after=time(17, 30),
        on_books_until=time(20, 0),
        ot_grace_minutes=30,
    )


def test_tuesday_ot_before_20_on_books():
    """Th3 — bấm 19:00 (sau 17:30), OT tính từ 17:00 → 120p sổ."""
    d = date(2025, 10, 7)  # Tuesday
    punches = [
        datetime(2025, 10, 7, 8, 0, tzinfo=VN),
        datetime(2025, 10, 7, 19, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(), ot_split=_policy())
    assert r.ot_on_books_minutes == 120
    assert r.ot_external_minutes == 0
    assert r.ot_minutes == 120


def test_tuesday_ot_after_20_external():
    """Th3 — sau 20:00 → OT ngoài."""
    d = date(2025, 10, 7)
    punches = [
        datetime(2025, 10, 7, 8, 0, tzinfo=VN),
        datetime(2025, 10, 7, 21, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(), ot_split=_policy())
    assert r.ot_on_books_minutes == 180  # 17:00-20:00
    assert r.ot_external_minutes == 60  # 20:00-21:00
    assert r.ot_minutes == 240


def test_wednesday_ot_all_external():
    """Th4 — toàn bộ OT → ngoài."""
    d = date(2025, 10, 8)  # Wednesday
    punches = [
        datetime(2025, 10, 8, 8, 0, tzinfo=VN),
        datetime(2025, 10, 8, 19, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(), ot_split=_policy())
    assert r.ot_on_books_minutes == 0
    assert r.ot_external_minutes == 120  # 17:00-19:00
    assert r.ot_minutes == 120


def test_split_helper_boundaries():
    policy = _policy()
    d = date(2025, 10, 7)
    shift_end = datetime(2025, 10, 7, 17, 0, tzinfo=VN)
    qualify = datetime(2025, 10, 7, 17, 30, tzinfo=VN)
    last_out = datetime(2025, 10, 7, 20, 0, tzinfo=VN)
    on_b, ext = split_weekday_ot_minutes(last_out, d, shift_end, qualify, policy)
    assert on_b == 180
    assert ext == 0


def test_toilet_grace_no_ot_before_qualify():
    """17:20 bấm ra — nghỉ cơm, không OT."""
    d = date(2025, 10, 3)  # Friday
    punches = [
        datetime(2025, 10, 3, 8, 0, tzinfo=VN),
        datetime(2025, 10, 3, 17, 20, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(), ot_split=_policy())
    assert r.ot_minutes == 0
    assert r.last_out == punches[1]


def test_ot_counts_from_1700_when_punch_after_dinner():
    """17:35 bấm ra — OT 35 phút (từ 17:00, không trừ 30 phút cơm)."""
    d = date(2025, 10, 3)  # Friday
    punches = [
        datetime(2025, 10, 3, 8, 0, tzinfo=VN),
        datetime(2025, 10, 3, 17, 35, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(), ot_split=_policy())
    assert r.ot_minutes == 35
    assert r.ot_external_minutes == 35


def test_dinner_punch_ignored_when_out_at_2000():
    """Bấm 17:20 (cơm) + 20:00 → bỏ 17:20; OT 17:00–20:00 = 180p."""
    d = date(2025, 10, 7)  # Tuesday
    punches = [
        datetime(2025, 10, 7, 8, 0, tzinfo=VN),
        datetime(2025, 10, 7, 17, 20, tzinfo=VN),
        datetime(2025, 10, 7, 20, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched(), ot_split=_policy())
    assert r.last_out == punches[2]
    assert r.ot_on_books_minutes == 180
    assert r.ot_external_minutes == 0
    assert r.ot_minutes == 180
    assert r.punch_count == 2
