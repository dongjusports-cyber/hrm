"""
Cắt phút OT theo khung giờ công ty Dongju.

Ngày thường / Thứ 7: 17–22 ×1,5 · 22–6 ×2,1 · 6–8 ×1,5. 8–17 là công, không OT.
Chủ nhật: 8–17 ×2,0 · 17–22 và 6–8 ×3,5 · 22–6 ×4,1.
Ngày lễ: cùng khung, ×3,0 / ×4,5 / ×5,1.

Qua nửa đêm: hệ số theo ngày lịch của từng phút (CN 22h–0h = 4,1, T2 0h–6h = 2,1).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Iterable

from app.modules.payroll.money import D, ZERO

RATE_KEYS = ("1.5", "2.1", "2.0", "3.5", "4.1", "3.0", "4.5", "5.1")

DEFAULT_BANDS: dict[str, dict[str, str]] = {
    "weekday": {"night": "2.1", "shoulder": "1.5", "core": "0", "evening": "1.5"},
    "sunday": {"night": "4.1", "shoulder": "3.5", "core": "2.0", "evening": "3.5"},
    "holiday": {"night": "5.1", "shoulder": "4.5", "core": "3.0", "evening": "4.5"},
}

NIGHT_RATES = frozenset({"2.1", "4.1", "5.1"})


def empty_channel_map() -> dict[str, dict[str, int]]:
    return {"on_books": {}, "external": {}}


def format_rate(rate: Decimal | str | float) -> str:
    return f"{D(rate):.1f}"


def day_kind(d: date, holiday_dates: set[date] | frozenset[date]) -> str:
    if d in holiday_dates:
        return "holiday"
    if d.isoweekday() == 7:
        return "sunday"
    return "weekday"


def clock_band(dt: datetime) -> str:
    minutes = dt.hour * 60 + dt.minute
    if minutes < 6 * 60:
        return "night"
    if minutes < 8 * 60:
        return "shoulder"
    if minutes < 17 * 60:
        return "core"
    if minutes < 22 * 60:
        return "evening"
    return "night"


def bands_from_policy(policy: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    rates = (policy or {}).get("ot_rates") or {}
    raw = rates.get("bands")
    if not isinstance(raw, dict):
        return DEFAULT_BANDS
    out = {k: dict(v) for k, v in DEFAULT_BANDS.items()}
    for kind in ("weekday", "sunday", "holiday"):
        block = raw.get(kind)
        if isinstance(block, dict):
            out[kind].update({str(bk): str(bv) for bk, bv in block.items()})
    return out


def rate_for_datetime(
    dt: datetime,
    holiday_dates: set[date] | frozenset[date],
    bands: dict[str, dict[str, str]] | None = None,
) -> Decimal:
    table = bands or DEFAULT_BANDS
    kind = day_kind(dt.date(), holiday_dates)
    band = clock_band(dt)
    return D(table.get(kind, DEFAULT_BANDS[kind]).get(band, "0"))


def _next_boundary(dt: datetime) -> datetime:
    d = dt.date()
    tz = dt.tzinfo
    candidates: list[datetime] = []
    for hour in (6, 8, 12, 13, 17, 22):
        cand = datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=tz)
        if cand > dt:
            candidates.append(cand)
    candidates.append(datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz) + timedelta(days=1))
    return min(candidates)


def _lunch_window(day: date, tz, lunch_start: time, lunch_end: time) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, lunch_start.hour, lunch_start.minute, tzinfo=tz)
    end = datetime(day.year, day.month, day.day, lunch_end.hour, lunch_end.minute, tzinfo=tz)
    return start, end


def _in_lunch(dt: datetime, lunch_start: time, lunch_end: time) -> bool:
    ls, le = _lunch_window(dt.date(), dt.tzinfo, lunch_start, lunch_end)
    return ls <= dt < le


def iter_paid_segments(
    start: datetime,
    end: datetime,
    *,
    skip_lunch: bool,
    lunch_start: time = time(12, 0),
    lunch_end: time = time(13, 0),
) -> Iterable[tuple[datetime, datetime]]:
    """Cắt [start, end) tại mốc 6/8/12/13/17/22h; CN/lễ bỏ 12h–13h."""
    if end <= start:
        return
    cursor = start
    while cursor < end:
        nxt = min(_next_boundary(cursor), end)
        if nxt > cursor and not (skip_lunch and _in_lunch(cursor, lunch_start, lunch_end)):
            yield cursor, nxt
        cursor = nxt


def add_interval_minutes(
    dest: dict[str, int],
    start: datetime,
    end: datetime,
    holiday_dates: set[date] | frozenset[date],
    *,
    skip_lunch: bool = False,
    lunch_start: time = time(12, 0),
    lunch_end: time = time(13, 0),
    bands: dict[str, dict[str, str]] | None = None,
    skip_zero_rate: bool = True,
) -> int:
    """Cộng phút theo hệ số vào dest. Trả tổng phút được tính."""
    total = 0
    table = bands or DEFAULT_BANDS
    for a, b in iter_paid_segments(
        start, end, skip_lunch=skip_lunch, lunch_start=lunch_start, lunch_end=lunch_end
    ):
        minutes = int((b - a).total_seconds() // 60)
        if minutes <= 0:
            continue
        rate = rate_for_datetime(a, holiday_dates, table)
        if skip_zero_rate and rate <= 0:
            continue
        key = format_rate(rate)
        dest[key] = dest.get(key, 0) + minutes
        total += minutes
    return total


def merge_rate_maps(*maps: dict[str, int] | None) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in maps:
        for k, v in (m or {}).items():
            if v:
                out[k] = out.get(k, 0) + int(v)
    return out


def minutes_map_to_hours(minutes_map: dict[str, int] | None) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for k, v in (minutes_map or {}).items():
        if v:
            out[k] = (Decimal(v) / Decimal(60)).quantize(Decimal("0.01"))
    return out


def hours_maps_sum(*maps: dict[str, Decimal] | None) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for m in maps:
        for k, v in (m or {}).items():
            hv = D(v)
            if hv:
                out[k] = out.get(k, ZERO) + hv
    return out


def night_minutes(minutes_map: dict[str, int] | None) -> int:
    return sum(int(v) for k, v in (minutes_map or {}).items() if k in NIGHT_RATES)
