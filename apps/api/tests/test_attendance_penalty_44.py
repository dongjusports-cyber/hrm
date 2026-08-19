"""4.4 — F_CAL_INDUS_AMT: miễn trừ trễ/sớm + vắng theo 22§22.3."""

from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal

from app.modules.attendance.engine import Schedule, calculate_day
from app.modules.payroll.attendance_penalty import (
    AttendanceDayPenaltyView,
    LeaveAdjustmentView,
    is_late_early_exempt,
    is_penalty_absence_day,
    summarize_attendance_penalties,
)
from app.modules.payroll.engine_allowances import AllowanceInput, AllowanceTypeView, compute_allowances
from app.modules.policy.seed_payload import default_payload

VN = timezone(timedelta(hours=7))
PEN = default_payload()["attendance_penalties"]


def _day(**kwargs) -> AttendanceDayPenaltyView:
    base = dict(
        work_date=date(2025, 10, 6),
        is_workday=True,
        leave_code=None,
        late_minutes=15,
        early_minutes=0,
        punch_count=2,
        first_in=datetime(2025, 10, 6, 8, 15, tzinfo=VN),
        last_out=datetime(2025, 10, 6, 17, 0, tzinfo=VN),
        worked_hours=Decimal("8"),
    )
    base.update(kwargs)
    return AttendanceDayPenaltyView(**base)


def test_exempt_ale_half_day_with_punch():
    day = _day(
        leave_code="ALE",
        worked_hours=Decimal("4"),
        late_minutes=20,
        first_in=datetime(2025, 10, 6, 13, 20, tzinfo=VN),
        last_out=datetime(2025, 10, 6, 17, 0, tzinfo=VN),
    )
    assert is_late_early_exempt(day, PEN) is True


def test_not_exempt_ale_full_day_no_punch():
    day = _day(
        leave_code="ALE",
        worked_hours=Decimal("0"),
        late_minutes=0,
        punch_count=0,
        first_in=None,
        last_out=None,
    )
    assert is_late_early_exempt(day, PEN) is False


def test_not_exempt_wrong_leave_code():
    day = _day(leave_code="TMP", worked_hours=Decimal("4"))
    assert is_late_early_exempt(day, PEN) is False


def test_late_exempt_does_not_count_toward_half_penalty():
    days = [
        _day(work_date=date(2025, 10, 6), late_minutes=10),
        _day(
            work_date=date(2025, 10, 7),
            leave_code="FLE",
            worked_hours=Decimal("4"),
            late_minutes=30,
            first_in=datetime(2025, 10, 7, 13, 30, tzinfo=VN),
            last_out=datetime(2025, 10, 7, 17, 0, tzinfo=VN),
        ),
        _day(work_date=date(2025, 10, 8), late_minutes=5),
    ]
    summary = summarize_attendance_penalties(days, [], contract_signed_at=date(2020, 1, 1), penalties=PEN)
    assert summary.raw_late_count == 3
    assert summary.exempt_late_days == 1
    assert summary.late_count == 2
    assert summary.early_count == 0


def test_absence_sle_counts_nop_from_adjustment():
    days = [
        _day(
            work_date=date(2025, 10, 9),
            leave_code="SLE",
            late_minutes=0,
            punch_count=0,
            first_in=None,
            last_out=None,
            worked_hours=Decimal("0"),
        )
    ]
    adjs = [LeaveAdjustmentView("NOP", Decimal("1"))]
    summary = summarize_attendance_penalties(
        days,
        adjs,
        contract_signed_at=date(2020, 1, 1),
        penalties=PEN,
    )
    assert summary.penalty_absent_days == Decimal("2")


def test_absence_ignored_during_probation():
    day = _day(
        work_date=date(2025, 10, 5),
        leave_code="NOP",
        late_minutes=0,
        punch_count=0,
        first_in=None,
        last_out=None,
    )
    assert is_penalty_absence_day(day, contract_signed_at=date(2025, 10, 15), penalties=PEN) is False
    summary = summarize_attendance_penalties([day], [], contract_signed_at=date(2025, 10, 15), penalties=PEN)
    assert summary.penalty_absent_days == 0


def test_absence_tmp_off_not_penalized():
    for code in ("TMP", "OFF", "ALE"):
        day = _day(leave_code=code, late_minutes=0, punch_count=0, worked_hours=Decimal("0"), first_in=None, last_out=None)
        assert is_penalty_absence_day(day, contract_signed_at=date(2020, 1, 1), penalties=PEN) is False


def test_compute_attend_zero_when_absent():
    types = [AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000"))]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("1"),
            join_date=None,
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=types,
        )
    )
    assert r.attend_keep_percent == 0
    assert r.lines[0].amount == 0


def test_three_lates_still_halves_without_exempt():
    days = [
        _day(work_date=date(2025, 10, i), late_minutes=5)
        for i in range(6, 9)
    ]
    summary = summarize_attendance_penalties(days, [], contract_signed_at=date(2020, 1, 1), penalties=PEN)
    assert summary.late_count == 3
    types = [AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000"))]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("27"),
            late_count=summary.late_count,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=None,
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=types,
        )
    )
    assert r.attend_keep_percent == 50
    assert r.lines[0].amount == Decimal("311538")


def _sched() -> Schedule:
    return Schedule(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(8, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(17, 0),
        grace_late_minutes=0,
        holiday_dates=set(),
    )


def _view_from_calc(d: date, r) -> AttendanceDayPenaltyView:
    return AttendanceDayPenaltyView(
        work_date=d,
        is_workday=r.is_workday,
        leave_code=None,
        late_minutes=r.late_minutes,
        early_minutes=r.early_minutes,
        punch_count=r.punch_count,
        first_in=r.first_in,
        last_out=r.last_out,
        worked_hours=r.worked_hours,
    )


def test_odd_punch_not_counted_until_hr_fills_pair():
    """Thiếu ra: ghi nhận vào, chưa đếm lần trễ. HR chấm tay đủ cặp → đếm trễ."""
    d = date(2025, 10, 6)
    odd = calculate_day([datetime(2025, 10, 6, 8, 15, tzinfo=VN)], d, _sched())
    assert odd.last_out is None
    assert odd.late_minutes == 0
    summary_odd = summarize_attendance_penalties(
        [_view_from_calc(d, odd)],
        [],
        contract_signed_at=date(2020, 1, 1),
        penalties=PEN,
    )
    assert summary_odd.late_count == 0

    filled = calculate_day(
        [datetime(2025, 10, 6, 8, 15, tzinfo=VN), datetime(2025, 10, 6, 17, 0, tzinfo=VN)],
        d,
        _sched(),
        explicit_pair=True,
    )
    assert filled.late_minutes == 15
    assert filled.early_minutes == 0
    summary = summarize_attendance_penalties(
        [_view_from_calc(d, filled)],
        [],
        contract_signed_at=date(2020, 1, 1),
        penalties=PEN,
    )
    assert summary.late_count == 1


def test_two_hr_late_days_halve_attendance_bonus():
    """Hai ngày HR xác nhận đi trễ (≥ 2) → chuyên cần còn 50%."""
    days = []
    for day_n in (6, 7):
        d = date(2025, 10, day_n)
        r = calculate_day(
            [datetime(2025, 10, day_n, 8, 15, tzinfo=VN), datetime(2025, 10, day_n, 17, 0, tzinfo=VN)],
            d,
            _sched(),
            explicit_pair=True,
        )
        assert r.late_minutes == 15
        days.append(_view_from_calc(d, r))
    summary = summarize_attendance_penalties(days, [], contract_signed_at=date(2020, 1, 1), penalties=PEN)
    assert summary.late_count == 2
    types = [AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000"))]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=summary.late_count,
            early_count=summary.early_count,
            penalty_absent_days=Decimal("0"),
            join_date=None,
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=types,
        )
    )
    assert r.attend_keep_percent == 50
