"""Ingest punches từ Agent — idempotent theo (MSNV, punch_time)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.attendance.engine import VN_TZ, to_vn
from app.modules.integration.bulk_ingest import bulk_insert_punches
from app.modules.integration.models import AttendancePunch, SyncJob
from app.modules.integration.punch_resolver import (
    backfill_unlinked_punches,
    build_employee_resolve_maps,
    direction_from_punch_in,
    exclude_patrol_guard_punches,
    is_patrol_guard_code,
    resolve_employee_id,
)
from app.modules.integration.schemas import (
    IntegrationStatusOut,
    MitaproPushRequest,
    MitaproPushResult,
    PunchOut,
    SyncJobOut,
    SyncJobsListOut,
    UnlinkedPunchesOut,
)

SYNC_STALE_HOURS = 24
SYNC_JOB_STALE_MINUTES = 45


def expire_stale_sync_jobs(db: Session, *, max_age_minutes: int = SYNC_JOB_STALE_MINUTES) -> int:
    """Job running/requested quá lâu → error (Agent crash hoặc push thất bại)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    rows = (
        db.query(SyncJob)
        .filter(
            SyncJob.source == "mitapro",
            SyncJob.status.in_(("requested", "running")),
            SyncJob.started_at < cutoff,
        )
        .all()
    )
    if not rows:
        return 0
    now = datetime.now(timezone.utc)
    for job in rows:
        job.status = "error"
        job.finished_at = now
        prev = (job.message or "").strip()
        job.message = (
            f"{prev} — Hết hạn sau {max_age_minutes} phút (Agent không hoàn tất). "
            "Kiểm tra Agent Mitapro và chạy lại Đồng bộ."
        ).strip()
    db.commit()
    return len(rows)


def normalize_punch_time(punch_time: datetime) -> datetime:
    """Mitapro gửi giờ VN — naive datetime coi là +07:00, không gắn UTC."""
    if punch_time.tzinfo is None:
        return punch_time.replace(tzinfo=VN_TZ)
    return punch_time


def verify_agent_token(token: str | None) -> None:
    settings = get_settings()
    expected = settings.agent_token
    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Trợ Lý AI: Agent token không hợp lệ. Kiểm tra AGENT_TOKEN.",
        )


def to_job_out(job: SyncJob) -> SyncJobOut:
    return SyncJobOut.model_validate(job)


def _is_mock_punch(ma_cham_cong: str | None) -> bool:
    """Agent --mock tạo MaChamCong MOCK-FP-* — không nạp vào HRM."""
    return bool(ma_cham_cong and str(ma_cham_cong).strip().upper().startswith("MOCK-FP-"))


def _recalc_after_ingest(db: Session, date_from: date, date_to: date) -> None:
    from app.modules.attendance.service import recalculate_days
    from app.modules.attendance.timesheet import rebuild_timesheets

    recalculate_days(db, date_from=date_from, date_to=date_to)
    y, m = date_from.year, date_from.month
    end_y, end_m = date_to.year, date_to.month
    while (y, m) <= (end_y, end_m):
        rebuild_timesheets(db, f"{y:04d}-{m:02d}", recalc_days=False)
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1


def _ingest_recalc_window(body: MitaproPushRequest, known_codes: set[str]) -> tuple[date, date] | None:
    """Khoảng ngày tính lại công — ưu tiên synced_from/to (Agent gửi khi sync khoảng lớn)."""
    if body.synced_from is not None and body.synced_to is not None:
        d_from = to_vn(normalize_punch_time(body.synced_from)).date()
        d_to = to_vn(normalize_punch_time(body.synced_to)).date()
        if d_to >= d_from:
            return d_from, d_to
    dates = [
        to_vn(normalize_punch_time(p.punch_time)).date()
        for p in body.punches
        if p.employee_code.strip() in known_codes
    ]
    if not dates:
        return None
    return min(dates), max(dates)


def ingest_punches(
    db: Session,
    body: MitaproPushRequest,
    *,
    trigger: str = "agent",
    claimed_job_id: UUID | None = None,
    schedule_recalc: bool = True,
    on_recalc_scheduled=None,
) -> MitaproPushResult:
    """Nhận batch punch; trùng (MSNV, thời điểm) thì bỏ qua.

    claimed_job_id: job HR đã claim — cập nhật cùng job thay vì tạo mới.
    schedule_recalc: False trong test đồng bộ; True → tính công nền sau response.
    on_recalc_scheduled: callback(job_id, date_from, date_to, partial, base_message).
    """
    if claimed_job_id is not None:
        job = db.get(SyncJob, claimed_job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trợ Lý AI: không tìm thấy job đồng bộ.",
            )
        job.status = "running"
        job.records_in += len(body.punches)
        job.message = "Đang nhận dữ liệu từ Agent…"
        job.trigger = trigger
        job.started_at = job.started_at or datetime.now(timezone.utc)
        job.finished_at = None
    else:
        job = SyncJob(
            status="running",
            records_in=len(body.punches),
            records_inserted=0,
            records_skipped=0,
            message="Đang nhận dữ liệu từ Agent…",
            source="mitapro",
            trigger=trigger,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
    db.flush()

    chunk_more = not body.chunk_final and bool(body.punches)

    maps = build_employee_resolve_maps(db)
    known_codes = set(maps.by_code.keys())
    mock_ignored = 0
    patrol_ignored = 0
    linked = 0
    unknown: list[str] = []
    prepared: list[dict] = []

    for p in body.punches:
        code = p.employee_code.strip()
        if is_patrol_guard_code(code):
            patrol_ignored += 1
            continue
        if _is_mock_punch(p.ma_cham_cong):
            mock_ignored += 1
            continue
        punch_time = normalize_punch_time(p.punch_time)
        emp_id = resolve_employee_id(maps, employee_code=code, ma_cham_cong=p.ma_cham_cong)
        if emp_id is None and code not in unknown:
            unknown.append(code)
        direction = direction_from_punch_in(p.direction, p.raw)
        prepared.append(
            {
                "employee_code": code,
                "employee_id": emp_id,
                "punch_time": punch_time,
                "direction": direction,
                "source": "mitapro",
                "ma_cham_cong": p.ma_cham_cong,
                "device_id": p.device_id,
                "raw": p.raw or {"employee_code": code},
            }
        )

    inserted, skipped, linked = bulk_insert_punches(db, sync_job_id=job.id, rows=prepared)
    if claimed_job_id is not None:
        job.records_inserted += inserted
        job.records_skipped += skipped
    else:
        job.records_inserted = inserted
        job.records_skipped = skipped

    partial = bool(unknown)
    if chunk_more and body.punches:
        job.message = (
            f"Đang nhận dữ liệu… {job.records_in} punch "
            f"({job.records_inserted} mới, {job.records_skipped} trùng)."
        )
        job.finished_at = None
        db.commit()
        db.refresh(job)
        return MitaproPushResult(
            job=to_job_out(job),
            detail=f"Trợ Lý AI: {job.message}",
        )

    if not body.punches:
        job.status = "success"
        job.message = "Agent gửi 0 punch."
        job.finished_at = datetime.now(timezone.utc)
    else:
        warn = ""
        if unknown:
            sample = ", ".join(unknown[:10])
            more = f"… (+{len(unknown) - 10})" if len(unknown) > 10 else ""
            warn = f" Cảnh báo: MSNV chưa có trong Nhân Sự: {sample}{more}."
        patrol_note = ""
        if patrol_ignored:
            patrol_note = f" Bỏ bảo vệ tuần (200*): {patrol_ignored}."
        mock_note = ""
        if mock_ignored:
            mock_note = f" Bỏ dữ liệu mock Agent: {mock_ignored}."
        base_message = (
            f"Đồng bộ: thêm {job.records_inserted}, bỏ trùng {job.records_skipped}, "
            f"khớp NV {linked}/{max(job.records_inserted, 1)}.{warn}{patrol_note}{mock_note}"
        ).strip()

        recalc_window = _ingest_recalc_window(body, known_codes)
        if (job.records_inserted > 0 or job.records_in > 0) and schedule_recalc and recalc_window is not None:
            d_from, d_to = recalc_window
            if get_settings().sync_recalc_inline:
                _recalc_after_ingest(db, d_from, d_to)
                base_message = f"{base_message} Đã tính lại công {d_from} → {d_to}."
            elif on_recalc_scheduled is not None:
                job.status = "running"
                job.message = f"{base_message} Đang tính lại công…"
                job.finished_at = None
                db.commit()
                db.refresh(job)
                on_recalc_scheduled(job.id, d_from, d_to, partial, base_message)
                return MitaproPushResult(job=to_job_out(job), detail=f"Trợ Lý AI: {job.message}")

        job.status = "partial" if partial else "success"
        job.message = base_message
        job.finished_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    from app.modules.ai.service import emit_sync_job_alert

    emit_sync_job_alert(db, job)

    return MitaproPushResult(job=to_job_out(job), detail=f"Trợ Lý AI: {job.message}")


def report_sync_error(db: Session, message: str, *, agent_name: str | None = None) -> SyncJobOut:
    """Agent báo lỗi đọc SQL / mạng — tạo sync_jobs error + AI alert."""
    name = (agent_name or "agent").strip() or "agent"
    job = SyncJob(
        status="error",
        records_in=0,
        records_inserted=0,
        records_skipped=0,
        message=f"[{name}] {message.strip()}",
        source="mitapro",
        trigger="agent",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.modules.ai.service import emit_sync_job_alert, evaluate_sync_streak

    emit_sync_job_alert(db, job)
    evaluate_sync_streak(db, streak=3)
    return to_job_out(job)


def request_sync_now(db: Session) -> SyncJobOut:
    """Nút Đồng bộ ngay — ghi job requested (Agent P2.2 sẽ đẩy dữ liệu)."""
    job = SyncJob(
        status="requested",
        records_in=0,
        message="Trợ Lý AI: đã yêu cầu đồng bộ. Agent trên máy Mitapro sẽ đẩy dữ liệu khi chạy (P2.2).",
        source="mitapro",
        trigger="manual",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return to_job_out(job)


def request_sync_range(db: Session, *, date_from: date, date_to: date) -> SyncJobOut:
    """Chạy lại một khoảng ngày — Agent đọc SQL theo sync_date_from/to."""
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: ngày đến phải >= ngày từ.")
    if (date_to - date_from).days > 92:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: khoảng ngày tối đa 92 ngày.")
    job = SyncJob(
        status="requested",
        records_in=0,
        message=(
            f"Trợ Lý AI: yêu cầu đồng bộ lại {date_from.isoformat()} → {date_to.isoformat()}. "
            "Agent Mitapro sẽ đọc SQL và đẩy punch."
        ),
        source="mitapro",
        trigger="manual",
        sync_date_from=date_from,
        sync_date_to=date_to,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return to_job_out(job)


def list_sync_jobs(db: Session, *, limit: int = 50, offset: int = 0) -> SyncJobsListOut:
    expire_stale_sync_jobs(db)
    lim = max(1, min(limit, 200))
    off = max(0, offset)
    q = db.query(SyncJob).filter(SyncJob.source == "mitapro")
    total = q.count()
    rows = q.order_by(SyncJob.started_at.desc()).offset(off).limit(lim).all()
    return SyncJobsListOut(total=total, items=[to_job_out(r) for r in rows])


def list_pending_requests(db: Session) -> list[SyncJobOut]:
    """Agent poll các yêu cầu Đồng bộ ngay."""
    rows = (
        db.query(SyncJob)
        .filter(SyncJob.status == "requested", SyncJob.source == "mitapro")
        .order_by(SyncJob.started_at.asc())
        .limit(20)
        .all()
    )
    return [to_job_out(r) for r in rows]


def claim_pending_request(db: Session, job_id) -> SyncJobOut:
    job = db.get(SyncJob, job_id)
    if job is None or job.status != "requested":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không còn yêu cầu đồng bộ này (đã xử lý hoặc không tồn tại).",
        )
    job.status = "running"
    job.message = "Agent đang đọc Mitapro và đẩy dữ liệu…"
    db.commit()
    db.refresh(job)
    return to_job_out(job)


def integration_status(db: Session) -> IntegrationStatusOut:
    expire_stale_sync_jobs(db)
    settings = get_settings()
    last = db.query(SyncJob).order_by(SyncJob.started_at.desc()).first()
    last_ok = (
        db.query(SyncJob)
        .filter(SyncJob.status.in_(["success", "partial"]))
        .order_by(SyncJob.finished_at.desc())
        .first()
    )
    count = exclude_patrol_guard_punches(db.query(AttendancePunch)).count()
    unlinked = exclude_patrol_guard_punches(
        db.query(AttendancePunch).filter(AttendancePunch.employee_id.is_(None))
    ).count()
    last_punch_at = exclude_patrol_guard_punches(db.query(func.max(AttendancePunch.punch_time))).scalar()
    configured = bool(settings.agent_token and settings.agent_token != "change_me_agent_token")
    detail = (
        "Agent đã cấu hình token."
        if configured
        else "Trợ Lý AI: chưa đổi AGENT_TOKEN mặc định — hãy đặt trong .env trước khi chạy Agent."
    )
    if last is None:
        detail += " Chưa có lần đồng bộ nào."
    else:
        detail += f" Lần sync gần nhất: {last.status} — {last.message}"

    now = datetime.now(timezone.utc)
    ref_at = last_ok.finished_at if last_ok and last_ok.finished_at else None
    if last_punch_at is not None:
        if ref_at is None or last_punch_at > ref_at:
            ref_at = last_punch_at
    hours_since = None
    stale = False
    if ref_at is not None:
        if ref_at.tzinfo is None:
            ref_at = ref_at.replace(tzinfo=timezone.utc)
        hours_since = (now - ref_at).total_seconds() / 3600.0
        stale = hours_since > SYNC_STALE_HOURS

    return IntegrationStatusOut(
        agent_configured=configured,
        last_job=to_job_out(last) if last else None,
        last_success_at=last_ok.finished_at if last_ok else None,
        punch_count=count,
        punch_unlinked_count=unlinked,
        last_punch_at=last_punch_at,
        stale_threshold_hours=SYNC_STALE_HOURS,
        hours_since_data=round(hours_since, 1) if hours_since is not None else None,
        stale_warning=stale,
        detail=detail,
    )


def list_unlinked_punches(db: Session, *, limit: int = 100) -> UnlinkedPunchesOut:
    lim = max(1, min(limit, 500))
    q = exclude_patrol_guard_punches(
        db.query(AttendancePunch)
        .filter(AttendancePunch.employee_id.is_(None))
        .order_by(AttendancePunch.punch_time.desc())
    )
    total = q.count()
    rows = q.limit(lim).all()
    return UnlinkedPunchesOut(
        total=total,
        items=[PunchOut.model_validate(r) for r in rows],
    )


def relink_punches(db: Session) -> dict[str, int]:
    """Admin — gắn employee_id cho punch mồ côi theo MSNV hiện có."""
    n = backfill_unlinked_punches(db)
    remaining = exclude_patrol_guard_punches(
        db.query(AttendancePunch).filter(AttendancePunch.employee_id.is_(None))
    ).count()
    return {"updated": n, "remaining_unlinked": remaining}
