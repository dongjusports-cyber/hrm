"""
Tách OT trên sổ vs OT ngoài (ATM riêng) — policy ot_split.

Quy tắc mặc định (Hiến pháp công ty):
- OT trong (sổ / AC-AD bảng lương): chỉ Thứ 3 và Thứ 5 (ISO 2, 4), 17:00–20:00.
- OT ngoài (ATM): T2/T4/T6/T7, sau 20:00 T3/T5, Chủ nhật, ngày lễ.
- Bấm 17:00–17:30: không tính vân tay (nếu còn bấm sau 17:30) và không OT.
- Bấm ra sau 17:30 mới có OT; số phút OT vẫn tính từ 17:00 (ra 20:00 = 180 phút).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload, normalize_si_policy

VN_TZ = timezone(timedelta(hours=7))


def _combine_vn(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=VN_TZ)


@dataclass(frozen=True)
class OtSplitPolicy:
    """Cấu hình tách OT — đọc từ policy ot_split."""

    on_books_weekdays: frozenset[int]  # isoweekday: 2=Th3, 4=Th5
    on_books_after: time  # ngưỡng bấm ra để được OT (17:30 — hết nghỉ cơm)
    on_books_until: time  # hết OT trên sổ (20:00)
    ot_grace_minutes: int = 30  # = on_books_after − hết ca; không trừ khỏi số phút OT
    ignore_punches_from: time = time(17, 0)
    ignore_punches_until: time = time(17, 30)


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


def _policy_from_raw(raw: dict, fallback: OtSplitPolicy | None = None) -> OtSplitPolicy:
    fb = fallback or OtSplitPolicy(
        on_books_weekdays=frozenset({2, 4}),
        on_books_after=time(17, 30),
        on_books_until=time(20, 0),
        ot_grace_minutes=30,
    )
    weekdays = raw.get("on_books_weekdays") or list(fb.on_books_weekdays)
    try:
        grace = int(raw.get("ot_grace_minutes", fb.ot_grace_minutes))
    except (TypeError, ValueError):
        grace = fb.ot_grace_minutes
    return OtSplitPolicy(
        on_books_weekdays=frozenset(int(x) for x in weekdays),
        on_books_after=_parse_hhmm(str(raw.get("on_books_after", "17:30")), fb.on_books_after),
        on_books_until=_parse_hhmm(str(raw.get("on_books_until", "20:00")), fb.on_books_until),
        ot_grace_minutes=max(0, grace),
        ignore_punches_from=_parse_hhmm(
            str(raw.get("ignore_punches_from", "17:00")), fb.ignore_punches_from
        ),
        ignore_punches_until=_parse_hhmm(
            str(raw.get("ignore_punches_until", "17:30")), fb.ignore_punches_until
        ),
    )


def default_ot_split_policy() -> OtSplitPolicy:
    seed = default_payload().get("ot_split") or {}
    return _policy_from_raw(seed if isinstance(seed, dict) else {})


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
    payload = normalize_si_policy(pkg.payload)
    raw = payload.get("ot_split")
    if not isinstance(raw, dict):
        return fallback
    try:
        return _policy_from_raw(raw, fallback)
    except (TypeError, ValueError):
        return fallback


def split_weekday_ot_minutes(
    last_out: datetime,
    work_date: date,
    ot_start: datetime,
    ot_qualify_after: datetime,
    policy: OtSplitPolicy,
) -> tuple[int, int]:
    """
    Trả (ot_on_books_minutes, ot_external_minutes) cho ngày làm việc thường.

    - ot_qualify_after (17:30): bấm ra ≤ mốc này → 0 OT (nghỉ cơm 17:00–17:30).
    - ot_start (mốc bắt đầu OT, MẶC ĐỊNH 17:00): số phút OT tính từ đây khi đã đủ ngưỡng.
      TÁCH khỏi giờ hết ca — ca CLEANER hết ca 16:00 nhưng OT vẫn từ 17:00,
      nên 16:00–17:00 (giờ nghỉ) không sinh OT (22§22.13, sửa LH-3).
    """
    if last_out <= ot_qualify_after:
        return 0, 0

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
