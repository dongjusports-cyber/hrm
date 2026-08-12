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
    Gom các lần bấm liên tiếp trong cửa sổ window_seconds.

    - Cụm đầu ngày: giữ thời điểm sớm nhất (giờ vào, vd. 07:45:20).
    - Cụm cuối ngày: giữ thời điểm muộn nhất (giờ ra, vd. 17:00:20).
    - Một cụm duy nhất: một mốc sớm nhất (vd. 5 lần bấm lúc 07:50 → một giờ vào).
    """
    if window_seconds <= 0 or not punches:
        return sorted(to_vn(p) for p in punches)

    times = sorted(to_vn(p) for p in punches)
    clusters = _cluster_punches(times, window_seconds)
    if len(clusters) == 1:
        return [clusters[0][0]]

    out: list[datetime] = []
    last_idx = len(clusters) - 1
    for i, cluster in enumerate(clusters):
        if i == 0:
            out.append(cluster[0])
        elif i == last_idx:
            out.append(cluster[-1])
        else:
            out.append(cluster[0])
    return out
