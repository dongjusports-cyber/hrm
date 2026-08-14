"""Tính lại công sau ingest — chạy nền để Agent HTTP trả về nhanh."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import UUID

from app.core.database import SessionLocal
from app.modules.integration.models import SyncJob

log = logging.getLogger(__name__)


def run_post_ingest_recalc(
    job_id: UUID,
    *,
    date_from: date,
    date_to: date,
    partial: bool,
    base_message: str,
) -> None:
    db = SessionLocal()
    try:
        from app.modules.attendance.service import recalculate_days
        from app.modules.attendance.timesheet import rebuild_timesheets
        from app.modules.ai.service import emit_sync_job_alert

        recalculate_days(db, date_from=date_from, date_to=date_to)
        for y, m in {(d.year, d.month) for d in _date_span(date_from, date_to)}:
            rebuild_timesheets(db, f"{y:04d}-{m:02d}", recalc_days=False)

        job = db.get(SyncJob, job_id)
        if job is None:
            return
        job.status = "partial" if partial else "success"
        job.message = f"{base_message} Đã tính lại công {date_from} → {date_to}."
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        emit_sync_job_alert(db, job)
    except Exception:
        log.exception("post_ingest_recalc failed job_id=%s", job_id)
        try:
            job = db.get(SyncJob, job_id)
            if job is not None:
                job.status = "error"
                job.message = f"{base_message} Lỗi tính lại công — xem log API."
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
                from app.modules.ai.service import emit_sync_job_alert

                emit_sync_job_alert(db, job)
        except Exception:
            log.exception("post_ingest_recalc could not mark job error")
    finally:
        db.close()


def _date_span(date_from: date, date_to: date):
    cur = date_from
    while cur <= date_to:
        yield cur
        cur = date.fromordinal(cur.toordinal() + 1)
