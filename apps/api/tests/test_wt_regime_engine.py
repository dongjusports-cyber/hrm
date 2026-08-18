"""Bước E — engine chế độ về sớm (22§22.14)."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.modules.attendance.engine import Schedule, calculate_day
from app.modules.attendance.ot_split import OtSplitPolicy

VN = timezone(timedelta(hours=7))


def _policy() -> OtSplitPolicy:
    return OtSplitPolicy(
        on_books_weekdays=frozenset({2, 4}),
        on_books_after=time(17, 30),
        on_books_until=time(20, 0),
        ot_grace_minutes=30,
    )


def _admin_sched(**kwargs) -> Schedule:
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


def _cleaner_sched(**kwargs) -> Schedule:
    base = dict(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(7, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(16, 0),
        grace_late_minutes=0,
        holiday_dates=set(),
    )
    base.update(kwargs)
    return Schedule(**base)


CLEANER_OT_START = time(17, 0)


def _punches(d: date, h_in: int, m_in: int, h_out: int, m_out: int) -> list[datetime]:
    return [
        datetime(d.year, d.month, d.day, h_in, m_in, tzinfo=VN),
        datetime(d.year, d.month, d.day, h_out, m_out, tzinfo=VN),
    ]


def test_pregnant_1h_out_1600_worked_8_early_0():
    """Thai sản 1h, ca ADMIN, ra 16:00 → worked=8, early=0."""
    d = date(2025, 10, 6)
    r = calculate_day(
        _punches(d, 8, 0, 16, 0),
        d,
        _admin_sched(),
        ot_split=_policy(),
        wt_hours_early=1,
    )
    assert r.worked_hours == Decimal("8")
    assert r.early_minutes == 0


def test_pregnant_1h_out_1500_worked_7_early_60():
    """Thai sản 1h, ra 15:00 → worked=7, early=60."""
    d = date(2025, 10, 6)
    r = calculate_day(
        _punches(d, 8, 0, 15, 0),
        d,
        _admin_sched(),
        ot_split=_policy(),
        wt_hours_early=1,
    )
    assert r.worked_hours == Decimal("7")
    assert r.early_minutes == 60


def test_no_regime_out_1700_worked_8_not_9():
    """Ra 17:00 không chế độ → worked=8 (không thành 9h)."""
    d = date(2025, 10, 6)
    r = calculate_day(_punches(d, 8, 0, 17, 0), d, _admin_sched(), ot_split=_policy())
    assert r.worked_hours == Decimal("8")
    assert r.early_minutes == 0


def test_child_2h_out_1500_worked_8_early_0():
    """Nuôi con 2h, ra 15:00 → worked=8, early=0."""
    d = date(2025, 10, 6)
    r = calculate_day(
        _punches(d, 8, 0, 15, 0),
        d,
        _admin_sched(),
        ot_split=_policy(),
        wt_hours_early=2,
    )
    assert r.worked_hours == Decimal("8")
    assert r.early_minutes == 0


def test_cleaner_pregnant_1h_allowed_out_1500():
    """Cleaner (hết ca 16:00) + Thai sản 1h → allowed_out 15:00, ra 15:00 không sớm."""
    d = date(2025, 10, 6)
    r = calculate_day(
        _punches(d, 7, 0, 15, 0),
        d,
        _cleaner_sched(),
        ot_split=_policy(),
        ot_start=CLEANER_OT_START,
        wt_hours_early=1,
    )
    assert r.early_minutes == 0
    assert r.worked_hours == Decimal("8")


def test_single_punch_no_bonus():
    """Chỉ 1 punch → không bù, worked=0."""
    d = date(2025, 10, 6)
    r = calculate_day(
        [datetime(2025, 10, 6, 8, 0, tzinfo=VN)],
        d,
        _admin_sched(),
        ot_split=_policy(),
        wt_hours_early=1,
    )
    assert r.punch_count == 1
    assert r.worked_hours == Decimal("0")


def test_regime_none_preserves_old_behavior():
    """wt_hours_early=None → hành vi cũ (ra 16:00 ADMIN = 7h công)."""
    d = date(2025, 10, 6)
    r = calculate_day(
        _punches(d, 8, 0, 16, 0),
        d,
        _admin_sched(),
        ot_split=_policy(),
        wt_hours_early=None,
    )
    assert r.worked_hours == Decimal("7")
    assert r.early_minutes == 60


def test_regime_not_on_holiday():
    """Ngày lễ — không áp dụng chế độ (worked=0 trên ngày nghỉ)."""
    d = date(2025, 10, 6)
    r = calculate_day(
        _punches(d, 8, 0, 16, 0),
        d,
        _admin_sched(holiday_dates={d}),
        ot_split=_policy(),
        wt_hours_early=1,
    )
    assert r.is_workday is False
    assert r.worked_hours == Decimal("0")
