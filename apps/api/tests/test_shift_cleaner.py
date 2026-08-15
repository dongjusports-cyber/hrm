"""Bước C — ca theo tổ (22§22.13): CLEANER hết ca 16:00, OT tách mốc 17:00.

Engine thuần (không DB): dựng Schedule của ca + truyền ot_start vào calculate_day.
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.modules.attendance.engine import Schedule, calculate_day
from app.modules.attendance.ot_split import OtSplitPolicy

VN = timezone(timedelta(hours=7))


def _policy() -> OtSplitPolicy:
    return OtSplitPolicy(
        on_books_weekdays=frozenset({2, 4}),
        on_books_after=time(17, 15),
        on_books_until=time(20, 0),
        ot_grace_minutes=15,
    )


def _cleaner_sched(**kwargs) -> Schedule:
    base = dict(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(7, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(16, 0),  # hết ca 16:00
        grace_late_minutes=0,
        holiday_dates=set(),
    )
    base.update(kwargs)
    return Schedule(**base)


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


CLEANER_OT_START = time(17, 0)


def test_cleaner_end_1600_is_normal_no_early_no_ot():
    """07:00–16:00 Th2: ra đúng giờ hết ca → không sớm, đủ 8 công, không OT."""
    d = date(2025, 10, 6)  # Monday
    punches = [datetime(2025, 10, 6, 7, 0, tzinfo=VN), datetime(2025, 10, 6, 16, 0, tzinfo=VN)]
    r = calculate_day(punches, d, _cleaner_sched(), ot_split=_policy(), ot_start=CLEANER_OT_START)
    assert r.early_minutes == 0
    assert r.late_minutes == 0
    assert r.worked_hours == Decimal("8")
    assert r.ot_minutes == 0


def test_cleaner_rest_hour_1600_1700_no_ot():
    """07:00–16:30: khoảng 16:00–17:00 là giờ nghỉ → không sinh OT dù có bấm."""
    d = date(2025, 10, 6)  # Monday
    punches = [datetime(2025, 10, 6, 7, 0, tzinfo=VN), datetime(2025, 10, 6, 16, 30, tzinfo=VN)]
    r = calculate_day(punches, d, _cleaner_sched(), ot_split=_policy(), ot_start=CLEANER_OT_START)
    assert r.ot_minutes == 0
    assert r.early_minutes == 0


def test_cleaner_ot_counts_from_1700_on_books_tuesday():
    """07:00–17:30 Th3: OT tính TỪ 17:00 (không phải 16:00) → 30p sổ."""
    d = date(2025, 10, 7)  # Tuesday (∈ on_books_weekdays)
    punches = [datetime(2025, 10, 7, 7, 0, tzinfo=VN), datetime(2025, 10, 7, 17, 30, tzinfo=VN)]
    r = calculate_day(punches, d, _cleaner_sched(), ot_split=_policy(), ot_start=CLEANER_OT_START)
    assert r.ot_on_books_minutes == 30
    assert r.ot_external_minutes == 0
    assert r.ot_minutes == 30


def test_cleaner_leave_before_1600_is_early():
    """07:00–15:00: ra trước 16:00 → về sớm 60 phút."""
    d = date(2025, 10, 6)  # Monday
    punches = [datetime(2025, 10, 6, 7, 0, tzinfo=VN), datetime(2025, 10, 6, 15, 0, tzinfo=VN)]
    r = calculate_day(punches, d, _cleaner_sched(), ot_split=_policy(), ot_start=CLEANER_OT_START)
    assert r.early_minutes == 60
    assert r.worked_hours == Decimal("7")
    assert r.ot_minutes == 0


def test_admin_regression_unchanged():
    """ADMIN 08:00–17:00: hành vi cũ giữ nguyên (ot_start mặc định = hết ca)."""
    d = date(2025, 10, 6)  # Monday
    punches = [datetime(2025, 10, 6, 8, 0, tzinfo=VN), datetime(2025, 10, 6, 17, 0, tzinfo=VN)]
    r = calculate_day(punches, d, _admin_sched(), ot_split=_policy())
    assert r.late_minutes == 0
    assert r.early_minutes == 0
    assert r.worked_hours == Decimal("8")
    assert r.ot_minutes == 0


def test_admin_ot_after_1715_still_from_1700():
    """ADMIN 08:00–17:20 Th3: OT vẫn từ 17:00 → 20p sổ (hồi quy ot_split)."""
    d = date(2025, 10, 7)  # Tuesday
    punches = [datetime(2025, 10, 7, 8, 0, tzinfo=VN), datetime(2025, 10, 7, 17, 20, tzinfo=VN)]
    r = calculate_day(punches, d, _admin_sched(), ot_split=_policy())
    assert r.ot_minutes == 20
    assert r.ot_on_books_minutes == 20
