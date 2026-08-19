"""3.2 — Lọc chấm vân tay liên tục (22§22.1, policy work_time.punch_dedupe)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

VN_TZ = timezone(timedelta(hours=7))

# 3.2 — nhiều lần bấm trong 1 phút gom thành 1 lần (policy work_time.punch_dedupe).
DEFAULT_DEDUPE_WINDOW_SECONDS = 60


def to_vn(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=VN_TZ)
    return dt.astimezone(VN_TZ)


def _cluster_punches(sorted_times: list[datetime], window_seconds: int) -> list[list[datetime]]:
    clusters: list[list[datetime]] = [[sorted_times[0]]]
    for t in sorted_times[1:]:
        if (t - clusters[-1][-1]).total_seconds() <= window_seconds:
            clusters[-1].append(t)
        else:
            clusters.append([t])
    return clusters


def dedupe_punch_times(
    punches: Sequence[datetime],
    *,
    window_seconds: int = DEFAULT_DEDUPE_WINDOW_SECONDS,
) -> list[datetime]:
    """
    Lần bấm đầu tiên trong ngày = vào, lần cuối cùng = ra, bỏ hết ở giữa.

    Ngoại lệ: cả ngày chỉ một chuỗi bấm trùng (mỗi lần ≤ window_seconds so với
    lần trước, vd. 07:54 / 07:55 / 07:56) → chỉ giữ lần đầu, không lấy lần
    cuối chuỗi làm giờ ra.
    """
    if not punches:
        return []
    times = sorted(to_vn(p) for p in punches)
    if window_seconds <= 0:
        if len(times) == 1:
            return times
        return [times[0], times[-1]]
    clusters = _cluster_punches(times, window_seconds)
    if len(clusters) == 1:
        return [clusters[0][0]]
    return [times[0], times[-1]]
