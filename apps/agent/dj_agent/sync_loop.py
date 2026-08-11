"""Vòng đồng bộ: lịch định kỳ + xử lý nút Đồng bộ ngay."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from dj_agent.config import AgentSettings
from dj_agent.pusher import ApiPusher
from dj_agent.sql_reader import PunchSource
from dj_agent.state import get_last_sync_at, set_last_sync_at

log = logging.getLogger("dj_agent")


def compute_window(settings: AgentSettings, now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    last = get_last_sync_at(settings.state_path)
    if last is None:
        dt_from = now - timedelta(days=settings.sync_lookback_days)
    else:
        dt_from = last - timedelta(minutes=settings.sync_overlap_minutes)
    return dt_from, now


def run_once(
    settings: AgentSettings,
    source: PunchSource,
    pusher: ApiPusher,
    *,
    reason: str = "schedule",
    dt_from: datetime | None = None,
    dt_to: datetime | None = None,
) -> dict:
    if dt_from is None or dt_to is None:
        dt_from, dt_to = compute_window(settings)
    log.info("[%s] Đọc Mitapro từ %s → %s", reason, dt_from.isoformat(), dt_to.isoformat())
    rows = source.fetch_punches(dt_from, dt_to)
    log.info("[%s] Đọc được %s punch", reason, len(rows))
    result = pusher.push_punches(
        rows,
        synced_from=dt_from.isoformat(),
        synced_to=dt_to.isoformat(),
    )
    job = result.get("job") or {}
    set_last_sync_at(
        settings.state_path,
        dt_to,
        extra={
            "last_reason": reason,
            "last_job_status": job.get("status"),
            "last_inserted": job.get("records_inserted"),
            "last_message": job.get("message"),
        },
    )
    log.info("[%s] %s", reason, result.get("detail") or job.get("message"))
    return result


def process_pending(settings: AgentSettings, source: PunchSource, pusher: ApiPusher) -> int:
    """Claim + sync các job requested từ Web."""
    pending = pusher.list_pending()
    done = 0
    for job in pending:
        jid = job.get("id")
        if not jid:
            continue
        try:
            pusher.claim_pending(jid)
            dt_from, dt_to = _window_from_job(job, settings)
            run_once(
                settings,
                source,
                pusher,
                reason="manual",
                dt_from=dt_from,
                dt_to=dt_to,
            )
            done += 1
        except Exception as exc:  # noqa: BLE001
            log.error("Lỗi xử lý pending %s: %s", jid, exc)
            _safe_report_error(pusher, f"Pending {jid}: {exc}")
    return done


def _window_from_job(job: dict, _settings: AgentSettings) -> tuple[datetime | None, datetime | None]:
    """Nếu Web yêu cầu khoảng ngày cố định — dùng sync_date_from/to."""
    raw_from = job.get("sync_date_from")
    raw_to = job.get("sync_date_to")
    if not raw_from or not raw_to:
        return None, None
    vn = timezone(timedelta(hours=7))
    try:
        y1, m1, d1 = (int(x) for x in str(raw_from).split("-"))
        y2, m2, d2 = (int(x) for x in str(raw_to).split("-"))
    except (TypeError, ValueError):
        return None, None
    dt_from = datetime(y1, m1, d1, 0, 0, 0, tzinfo=vn)
    dt_to = datetime(y2, m2, d2, 23, 59, 59, tzinfo=vn)
    return dt_from, dt_to


def _safe_report_error(pusher: ApiPusher, message: str) -> None:
    try:
        pusher.report_error(message)
    except Exception as report_exc:  # noqa: BLE001
        log.error("Không gửi được báo lỗi lên API: %s", report_exc)


def run_forever(settings: AgentSettings, source: PunchSource, pusher: ApiPusher) -> None:
    interval = max(0, settings.sync_interval_minutes)
    log.info(
        "DJ Agent bắt đầu — API=%s · interval=%s phút · mock=%s",
        settings.dj_api_base_url,
        interval,
        settings.dj_agent_mock_sql,
    )
    while True:
        try:
            process_pending(settings, source, pusher)
            run_once(settings, source, pusher, reason="schedule")
        except Exception as exc:  # noqa: BLE001
            log.error("Trợ Lý AI / Agent lỗi sync: %s", exc)
            _safe_report_error(pusher, str(exc))
        if interval <= 0:
            log.info("SYNC_INTERVAL_MINUTES=0 → chạy 1 lần rồi thoát.")
            break
        time.sleep(interval * 60)
