"""
Tách OT trên sổ vs OT ngoài (ATM riêng) — policy ot_split.

Quy tắc mặc định (Hiến pháp công ty):
- Thứ 3, Thứ 5 (ISO 2, 4): OT 17:00–20:00 → sổ; sau 20:00 → ngoài.
- Chỉ tính OT khi bấm ra sau 17:15 (grace toilet); nhưng số phút OT vẫn tính từ 17:00.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload

VN_TZ = timezone(timedelta(hours=7))


def _combine_vn(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=VN_TZ)


@dataclass(frozen=True)
class OtSplitPolicy:
    """Cấu hình tách OT — đọc từ policy ot_split."""

    on_books_weekdays: frozenset[int]  # isoweekday: 2=Th3, 4=Th5
    on_books_after: time  # ngưỡng bấm ra để được OT (17:15 — grace toilet)
    on_books_until: time  # hết OT trên sổ (20:00)
    ot_grace_minutes: int = 15  # = on_books_after − hết ca; không trừ khỏi số phút OT


def _parse_hhmm(value: str, fallback: time) -> time:
    raw = (value or "").strip()
    if not raw:
        return fallback
    parts = raw.split(":")
    try:
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        return time(h, m)
    except (TypeError, ValueError):
        return fallback


def default_ot_split_policy() -> OtSplitPolicy:
    seed = default_payload().get("ot_split") or {}
    weekdays = seed.get("on_books_weekdays") or [2, 4]
    try:
        grace = int(seed.get("ot_grace_minutes", 15))
    except (TypeError, ValueError):
        grace = 15
    return OtSplitPolicy(
        on_books_weekdays=frozenset(int(x) for x in weekdays),
        on_books_after=_parse_hhmm(str(seed.get("on_books_after", "17:15")), time(17, 15)),
        on_books_until=_parse_hhmm(str(seed.get("on_books_until", "20:00")), time(20, 0)),
        ot_grace_minutes=max(0, grace),
    )


def load_ot_split_policy(db: Session) -> OtSplitPolicy:
    fallback = default_ot_split_policy()
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if not pkg or not isinstance(pkg.payload, dict):
        return fallback
    raw = pkg.payload.get("ot_split")
    if not isinstance(raw, dict):
        return fallback
    try:
        weekdays = raw.get("on_books_weekdays", list(fallback.on_books_weekdays))
        try:
            grace = int(raw.get("ot_grace_minutes", fallback.ot_grace_minutes))
        except (TypeError, ValueError):
            grace = fallback.ot_grace_minutes
        return OtSplitPolicy(
            on_books_weekdays=frozenset(int(x) for x in weekdays),
            on_books_after=_parse_hhmm(str(raw.get("on_books_after", "17:15")), fallback.on_books_after),
            on_books_until=_parse_hhmm(str(raw.get("on_books_until", "20:00")), fallback.on_books_until),
            ot_grace_minutes=max(0, grace),
        )
    except (TypeError, ValueError):
        return fallback


def split_weekday_ot_minutes(
    last_out: datetime,
    work_date: date,
    shift_end: datetime,
    ot_qualify_after: datetime,
    policy: OtSplitPolicy,
) -> tuple[int, int]:
    """
    Trả (ot_on_books_minutes, ot_external_minutes) cho ngày làm việc thường.

    - ot_qualify_after (17:15): bấm ra ≤ mốc này → 0 OT (toilet / việc riêng).
    - shift_end (17:00): khi đủ điều kiện, số phút OT tính từ hết ca (vd. 17:16 → 16p).
    """
    if last_out <= ot_qualify_after:
        return 0, 0

    ot_start = shift_end
    ot_end = last_out
    total = int((ot_end - ot_start).total_seconds() // 60)
    if total <= 0:
        return 0, 0

    if work_date.isoweekday() not in policy.on_books_weekdays:
        return 0, total

    cutoff = _combine_vn(work_date, policy.on_books_until)
    if ot_end <= cutoff:
        return total, 0
    if ot_start >= cutoff:
        return 0, total

    on_books = int((min(ot_end, cutoff) - ot_start).total_seconds() // 60)
    external = int((ot_end - cutoff).total_seconds() // 60)
    return max(0, on_books), max(0, external)
