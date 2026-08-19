"""
Tính late / early / ot_minutes từ punch thô + lịch công ty (04§4.3, 3.3).
Ca 08:00–17:00, trừ 1 giờ trưa; dung sai trễ/sớm theo giây.
Luật OT (cổng, Cooker, 8 hệ số, theo phút): Luật/02-OT.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from app.modules.attendance.ot_bands import add_interval_minutes, empty_channel_map
from app.modules.attendance.ot_split import OtSplitPolicy, default_ot_split_policy
from app.modules.attendance.punch_dedupe import dedupe_punch_times

VN_TZ = timezone(timedelta(hours=7))


@dataclass(frozen=True)
class Schedule:
    work_weekdays: list[int]  # 1=Mon..7=Sun
    morning_start: time
    morning_end: time
    afternoon_start: time
    afternoon_end: time
    grace_late_minutes: int
    holiday_dates: set[date]
    grace_late_seconds: int = 0
    grace_early_seconds: int = 0


@dataclass
class DayCalcResult:
    work_date: date
    first_in: datetime | None
    last_out: datetime | None
    worked_hours: Decimal
    late_minutes: int
    early_minutes: int
    ot_minutes: int
    ot_on_books_minutes: int
    ot_external_minutes: int
    ot_type: str | None
    punch_count: int
    is_workday: bool
    ot_rate_minutes: dict = field(default_factory=dict)


def to_vn(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=VN_TZ)
    return dt.astimezone(VN_TZ)


def combine_vn(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=VN_TZ)


def is_company_workday(d: date, schedule: Schedule) -> bool:
    if d in schedule.holiday_dates:
        return False
    return d.isoweekday() in set(schedule.work_weekdays)


def _seconds_to_minutes_up(seconds: float) -> int:
    """Dung sai 0 giây — trễ/sớm 1 giây cũng tính ít nhất 1 phút."""
    if seconds <= 0:
        return 0
    return int((seconds + 59) // 60)


def _drop_interval_punches_if_later(
    times: list[datetime],
    work_date: date,
    start: time,
    end: time,
) -> list[datetime]:
    """Bỏ vân tay trong [start, end] khi đã có bấm sau end (nghỉ cơm 17:00–17:30).

    Chỉ về nhà trong khung này → giữ mốc để ghi giờ ra, không OT (ngưỡng 17:30).
    """
    if not times:
        return times
    t0 = combine_vn(work_date, start)
    t1 = combine_vn(work_date, end)
    if not any(t > t1 for t in times):
        return times
    return [t for t in times if t < t0 or t > t1]


def _assign_single_punch(
    punch: datetime,
    schedule: Schedule,
    work_date: date,
) -> tuple[datetime | None, datetime | None]:
    """
    Một lần bấm sau dedupe — gán vào cột vào hoặc ra (HR/AI thấy, không bỏ trống cả hai).

    Từ 13:00 trở đi coi là giờ ra; sáng coi là giờ vào.
    """
    split = combine_vn(work_date, schedule.afternoon_start)
    if punch >= split:
        return None, punch
    return punch, None


def _resolve_in_out_from_times(
    times: list[datetime],
    schedule: Schedule,
    work_date: date,
) -> tuple[datetime | None, datetime | None]:
    """
    Gán giờ vào / ra sau dedupe.

    - Trước giờ vào ca: mọi lần bấm = thử vào (giữ sớm nhất).
    - Từ giờ vào ca đến trước nghỉ trưa (morning_end): vẫn coi là vào, không coi mốc sau là ra.
    - Từ nghỉ trưa trở đi: mốc muộn nhất = ra (nhiều lần bấm chiều gom một).
    - Không có giờ vào buổi sáng nhưng có ≥2 mốc sau nghỉ trưa, cách nhau ≥60 phút
      (vd. 12:30 + 17:07): mốc sớm = vào, mốc muộn = ra — công buổi chiều, ghi nhận đi trễ.
    """
    shift_start = combine_vn(work_date, schedule.morning_start)
    depart_after = combine_vn(work_date, schedule.morning_end)

    pre_shift = [t for t in times if t < shift_start]
    rest = [t for t in times if t >= shift_start]

    first_in = min(pre_shift) if pre_shift else None

    arrivals = [t for t in rest if t < depart_after]
    departures = [t for t in rest if t >= depart_after]

    if arrivals:
        first_in = min(arrivals) if first_in is None else min(first_in, min(arrivals))

    if not departures:
        return first_in, None

    last_out = max(departures)
    # Nghỉ sáng / vào muộn sau 12:00: đừng nuốt mốc sớm thành «chỉ có giờ ra».
    if first_in is None and len(departures) >= 2:
        earliest = min(departures)
        if (last_out - earliest).total_seconds() >= 60 * 60:
            first_in = earliest
    return first_in, last_out


def _calc_partial_workday(
    *,
    first_in: datetime | None,
    last_out: datetime | None,
    work_date: date,
    schedule: Schedule,
    split_policy: OtSplitPolicy,
    ot_start: time | None = None,
    morning_ot_from: time | None = None,
    morning_ot_qualify_before: time | None = None,
) -> tuple[int, int, int, int, int, Decimal, str | None, dict]:
    """Late / early / OT / worked khi thiếu vào hoặc thiếu ra."""
    shift_start = combine_vn(work_date, schedule.morning_start) + timedelta(
        seconds=schedule.grace_late_seconds,
        minutes=schedule.grace_late_minutes,
    )
    shift_end = combine_vn(work_date, schedule.afternoon_end)
    early_deadline = shift_end - timedelta(seconds=schedule.grace_early_seconds)

    late = 0
    early = 0
    ot_on_books = 0
    ot_external = 0
    ot_type: str | None = None
    rates = empty_channel_map()

    if first_in is not None and last_out is None:
        if first_in > shift_start:
            late = _seconds_to_minutes_up((first_in - shift_start).total_seconds())
        worked = Decimal("0")
    elif last_out is not None and first_in is None:
        if last_out < early_deadline:
            early = _seconds_to_minutes_up((early_deadline - last_out).total_seconds())
        rates = _allocate_workday_ot(
            first_in=None,
            last_out=last_out,
            work_date=work_date,
            schedule=schedule,
            split_policy=split_policy,
            ot_start=ot_start,
            morning_ot_from=morning_ot_from,
            morning_ot_qualify_before=morning_ot_qualify_before,
        )
        ot_on_books = _sum_rate_map(rates["on_books"])
        ot_external = _sum_rate_map(rates["external"])
        ot = ot_on_books + ot_external
        ot_type = "weekday" if ot > 0 else None
        worked = Decimal("0")
    else:
        worked = Decimal("0")

    ot = ot_on_books + ot_external
    return late, early, ot, ot_on_books, ot_external, worked, ot_type, rates


def _apply_wt_regime(
    *,
    last_out: datetime,
    work_date: date,
    schedule: Schedule,
    actual_worked: Decimal,
    wt_hours_early: int,
    standard_hours: Decimal,
) -> tuple[int, Decimal]:
    """Điều chỉnh early/worked theo chế độ về sớm (22§22.14).

    Chỉ gọi khi đủ vào+ra trên ngày công. allowed_out = hết ca − hours_early.
    """
    allowed_out = combine_vn(work_date, schedule.afternoon_end) - timedelta(hours=wt_hours_early)
    bonus = Decimal(str(wt_hours_early))
    if last_out >= allowed_out:
        early = 0
        worked = min(actual_worked + bonus, standard_hours)
    else:
        early = _seconds_to_minutes_up((allowed_out - last_out).total_seconds())
        worked = min(actual_worked + bonus, standard_hours)
    return early, worked


def _lunch_overlap_seconds(
    first_in: datetime,
    last_out: datetime,
    schedule: Schedule,
    work_date: date,
) -> float:
    """Số giây chồng lên khung nghỉ trưa (morning_end → afternoon_start)."""
    lunch_start = combine_vn(work_date, schedule.morning_end)
    lunch_end = combine_vn(work_date, schedule.afternoon_start)
    overlap_start = max(first_in, lunch_start)
    overlap_end = min(last_out, lunch_end)
    if overlap_end <= overlap_start:
        return 0.0
    return (overlap_end - overlap_start).total_seconds()


def _shift_worked_hours(
    first_in: datetime,
    last_out: datetime,
    schedule: Schedule,
    work_date: date,
) -> Decimal:
    """Giờ công trong khung ca (08:00–17:00), trừ nghỉ trưa — không cộng OT vào công."""
    shift_start = combine_vn(work_date, schedule.morning_start)
    shift_end = combine_vn(work_date, schedule.afternoon_end)
    seg_in = max(first_in, shift_start)
    seg_out = min(last_out, shift_end)
    if seg_out <= seg_in:
        return Decimal("0")
    total = Decimal(str((seg_out - seg_in).total_seconds() / 3600))
    lunch_h = Decimal(str(_lunch_overlap_seconds(seg_in, seg_out, schedule, work_date) / 3600))
    total -= lunch_h
    if total < 0:
        total = Decimal("0")
    return total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _sum_rate_map(m: dict[str, int] | None) -> int:
    return sum(int(v) for v in (m or {}).values())


def _rest_day_paid_start(
    first_in: datetime,
    work_date: date,
    schedule: Schedule,
    morning_ot_from: time | None,
    morning_ot_qualify_before: time | None,
) -> datetime:
    """CN/lễ: kẹp giờ vào ca. Cooker bấm trước 6:00 → bắt đầu trả từ 6:00."""
    shift_start = combine_vn(work_date, schedule.morning_start)
    if (
        morning_ot_from is not None
        and morning_ot_qualify_before is not None
        and first_in < combine_vn(work_date, morning_ot_qualify_before)
    ):
        return combine_vn(work_date, morning_ot_from)
    if first_in < shift_start:
        return shift_start
    return first_in


def _allocate_morning_ot(
    rates: dict,
    *,
    first_in: datetime | None,
    last_out: datetime | None,
    work_date: date,
    schedule: Schedule,
    morning_ot_from: time | None,
    morning_ot_qualify_before: time | None,
) -> None:
    """OT sáng chỉ khi bấm trước mốc qualify (Cooker: trước 6:00). Phút từ paid_from đến giờ vào ca."""
    if morning_ot_from is None or morning_ot_qualify_before is None:
        return
    if first_in is None or last_out is None:
        return
    gate = combine_vn(work_date, morning_ot_qualify_before)
    if first_in >= gate:
        return
    paid_from = combine_vn(work_date, morning_ot_from)
    paid_until = combine_vn(work_date, schedule.morning_start)
    end = min(last_out, paid_until)
    if end <= paid_from:
        return
    add_interval_minutes(
        rates["external"],
        paid_from,
        end,
        schedule.holiday_dates,
        skip_lunch=False,
    )


def _allocate_rest_day_ot(
    first_in: datetime,
    last_out: datetime,
    schedule: Schedule,
    work_date: date,
    morning_ot_from: time | None = None,
    morning_ot_qualify_before: time | None = None,
) -> dict:
    rates = empty_channel_map()
    paid_start = _rest_day_paid_start(
        first_in, work_date, schedule, morning_ot_from, morning_ot_qualify_before
    )
    add_interval_minutes(
        rates["external"],
        paid_start,
        last_out,
        schedule.holiday_dates,
        skip_lunch=True,
        lunch_start=schedule.morning_end,
        lunch_end=schedule.afternoon_start,
    )
    return rates


def _allocate_workday_ot(
    *,
    first_in: datetime | None,
    last_out: datetime | None,
    work_date: date,
    schedule: Schedule,
    split_policy: OtSplitPolicy,
    ot_start: time | None,
    morning_ot_from: time | None = None,
    morning_ot_qualify_before: time | None = None,
) -> dict:
    """OT chiều sau 17:30 (phút từ 17:00); OT sáng chỉ Cooker khi bấm trước 6:00. T3/T5 17–20 vào sổ."""
    rates = empty_channel_map()
    holidays = schedule.holiday_dates
    _allocate_morning_ot(
        rates,
        first_in=first_in,
        last_out=last_out,
        work_date=work_date,
        schedule=schedule,
        morning_ot_from=morning_ot_from,
        morning_ot_qualify_before=morning_ot_qualify_before,
    )

    if last_out is None:
        return rates

    ot_start_dt = combine_vn(work_date, ot_start or schedule.afternoon_end)
    ot_qualify_after = ot_start_dt + timedelta(minutes=split_policy.ot_grace_minutes)
    if last_out <= ot_qualify_after:
        return rates

    on_books_days = work_date.isoweekday() in split_policy.on_books_weekdays
    cutoff = combine_vn(work_date, split_policy.on_books_until)
    if on_books_days:
        books_end = min(last_out, cutoff)
        if books_end > ot_start_dt:
            add_interval_minutes(rates["on_books"], ot_start_dt, books_end, holidays, skip_lunch=False)
        if last_out > cutoff:
            ext_start = max(ot_start_dt, cutoff)
            if last_out > ext_start:
                add_interval_minutes(rates["external"], ext_start, last_out, holidays, skip_lunch=False)
    else:
        add_interval_minutes(rates["external"], ot_start_dt, last_out, holidays, skip_lunch=False)
    return rates


def calculate_day(
    punches: Sequence[datetime],
    work_date: date,
    schedule: Schedule,
    *,
    punch_dedupe_window_seconds: int = 60,
    ot_split: OtSplitPolicy | None = None,
    ot_start: time | None = None,
    wt_hours_early: int | None = None,
    standard_hours: Decimal | None = None,
    morning_ot_from: time | None = None,
    morning_ot_qualify_before: time | None = None,
) -> DayCalcResult:
    split_policy = ot_split or default_ot_split_policy()
    times = dedupe_punch_times(punches, window_seconds=punch_dedupe_window_seconds)
    if times and is_company_workday(work_date, schedule):
        times = _drop_interval_punches_if_later(
            times,
            work_date,
            split_policy.ignore_punches_from,
            split_policy.ignore_punches_until,
        )
    if not times:
        return DayCalcResult(
            work_date=work_date,
            first_in=None,
            last_out=None,
            worked_hours=Decimal("0"),
            late_minutes=0,
            early_minutes=0,
            ot_minutes=0,
            ot_on_books_minutes=0,
            ot_external_minutes=0,
            ot_type=None,
            punch_count=0,
            is_workday=is_company_workday(work_date, schedule),
        )

    # Một mốc sau dedupe — ghi nhận giờ vào HOẶC giờ ra (HR/AI rà soát).
    if len(times) == 1:
        punch = times[0]
        workday = is_company_workday(work_date, schedule)
        first_in, last_out = _assign_single_punch(punch, schedule, work_date)
        late = early = ot = ot_on_books = ot_external = 0
        ot_type: str | None = None
        worked = Decimal("0")
        rates = empty_channel_map()
        if workday:
            late, early, ot, ot_on_books, ot_external, worked, ot_type, rates = _calc_partial_workday(
                first_in=first_in,
                last_out=last_out,
                work_date=work_date,
                schedule=schedule,
                split_policy=split_policy,
                ot_start=ot_start,
                morning_ot_from=morning_ot_from,
                morning_ot_qualify_before=morning_ot_qualify_before,
            )
        return DayCalcResult(
            work_date=work_date,
            first_in=first_in,
            last_out=last_out,
            worked_hours=worked,
            late_minutes=late,
            early_minutes=early,
            ot_minutes=ot,
            ot_on_books_minutes=ot_on_books,
            ot_external_minutes=ot_external,
            ot_type=ot_type,
            punch_count=1,
            is_workday=workday,
            ot_rate_minutes=rates,
        )

    first_in, last_out = _resolve_in_out_from_times(times, schedule, work_date)
    workday = is_company_workday(work_date, schedule)
    late = 0
    early = 0
    ot = 0
    ot_on_books = 0
    ot_external = 0
    ot_type = None
    rates = empty_channel_map()

    if workday:
        if first_in is not None and last_out is not None:
            shift_start = combine_vn(work_date, schedule.morning_start) + timedelta(
                seconds=schedule.grace_late_seconds,
                minutes=schedule.grace_late_minutes,
            )
            shift_end = combine_vn(work_date, schedule.afternoon_end)
            early_deadline = shift_end - timedelta(seconds=schedule.grace_early_seconds)

            if first_in > shift_start:
                late = _seconds_to_minutes_up((first_in - shift_start).total_seconds())
            if last_out < early_deadline:
                early = _seconds_to_minutes_up((early_deadline - last_out).total_seconds())
            rates = _allocate_workday_ot(
                first_in=first_in,
                last_out=last_out,
                work_date=work_date,
                schedule=schedule,
                split_policy=split_policy,
                ot_start=ot_start,
                morning_ot_from=morning_ot_from,
                morning_ot_qualify_before=morning_ot_qualify_before,
            )
            ot_on_books = _sum_rate_map(rates["on_books"])
            ot_external = _sum_rate_map(rates["external"])
            ot = ot_on_books + ot_external
            ot_type = "weekday" if ot > 0 else None
            worked = _shift_worked_hours(first_in, last_out, schedule, work_date)
            if wt_hours_early:
                early, worked = _apply_wt_regime(
                    last_out=last_out,
                    work_date=work_date,
                    schedule=schedule,
                    actual_worked=worked,
                    wt_hours_early=wt_hours_early,
                    standard_hours=standard_hours or Decimal("8"),
                )
        else:
            late, early, ot, ot_on_books, ot_external, worked, ot_type, rates = _calc_partial_workday(
                first_in=first_in,
                last_out=last_out,
                work_date=work_date,
                schedule=schedule,
                split_policy=split_policy,
                ot_start=ot_start,
                morning_ot_from=morning_ot_from,
                morning_ot_qualify_before=morning_ot_qualify_before,
            )
    else:
        # CN/lễ: OT từ giờ vào ca (kẹp); Cooker đủ cổng 6:00 thì từ 6:00. Trừ cơm.
        first_in = times[0]
        last_out = times[-1]
        rates = _allocate_rest_day_ot(
            first_in,
            last_out,
            schedule,
            work_date,
            morning_ot_from=morning_ot_from,
            morning_ot_qualify_before=morning_ot_qualify_before,
        )
        ot_external = _sum_rate_map(rates["external"])
        ot_on_books = 0
        ot = ot_external
        ot_type = "holiday" if work_date in schedule.holiday_dates else "weekend"
        worked = Decimal("0")

    return DayCalcResult(
        work_date=work_date,
        first_in=first_in,
        last_out=last_out,
        worked_hours=worked,
        late_minutes=late,
        early_minutes=early,
        ot_minutes=ot,
        ot_on_books_minutes=ot_on_books,
        ot_external_minutes=ot_external,
        ot_type=ot_type,
        punch_count=len(times),
        is_workday=workday,
        ot_rate_minutes=rates,
    )
