"""Ingest punches từ Agent — idempotent theo (MSNV, punch_time)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.attendance.engine import VN_TZ, to_vn
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


def ingest_punches(
    db: Session, body: MitaproPushRequest, *, trigger: str = "agent"
) -> MitaproPushResult:
    """Nhận batch punch; trùng (MSNV, thời điểm) thì bỏ qua."""
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

    maps = build_employee_resolve_maps(db)
    known_codes = set(maps.by_code.keys())
    inserted = 0
    skipped = 0
    patrol_ignored = 0
    linked = 0
    unknown: list[str] = []

    for p in body.punches:
        code = p.employee_code.strip()
        if is_patrol_guard_code(code):
            patrol_ignored += 1
            continue
        punch_time = normalize_punch_time(p.punch_time)

        emp_id = resolve_employee_id(maps, employee_code=code, ma_cham_cong=p.ma_cham_cong)
        if emp_id is None and code not in unknown:
            unknown.append(code)

        direction = direction_from_punch_in(p.direction, p.raw)

        nested = db.begin_nested()
        try:
            db.add(
                AttendancePunch(
                    employee_code=code,
                    employee_id=emp_id,
                    punch_time=punch_time,
                    direction=direction,
                    sync_job_id=job.id,
                    source="mitapro",
                    ma_cham_cong=p.ma_cham_cong,
                    device_id=p.device_id,
                    raw=p.raw or {"employee_code": code},
                )
            )
            db.flush()
            nested.commit()
            inserted += 1
            if emp_id is not None:
                linked += 1
        except IntegrityError:
            nested.rollback()
            skipped += 1

    job.records_inserted = inserted
    job.records_skipped = skipped
    job.finished_at = datetime.now(timezone.utc)

    if not body.punches:
        job.status = "success"
        job.message = "Agent gửi 0 punch."
    else:
        warn = ""
        if unknown:
            sample = ", ".join(unknown[:10])
            more = f"… (+{len(unknown) - 10})" if len(unknown) > 10 else ""
            warn = f" Cảnh báo: MSNV chưa có trong Nhân Sự: {sample}{more}."
            job.status = "partial"
        else:
            job.status = "success"
        patrol_note = ""
        if patrol_ignored:
            patrol_note = f" Bỏ bảo vệ tuần (200*): {patrol_ignored}."
        job.message = (
            f"Đồng bộ: thêm {inserted}, bỏ trùng {skipped}, khớp NV {linked}/{inserted}.{warn}{patrol_note}"
        ).strip()

    db.commit()
    db.refresh(job)

    # P2.5 — Lớp A: sync partial/error → nhắc Admin
    from app.modules.ai.service import emit_sync_job_alert

    emit_sync_job_alert(db, job)

    # P2.3 — tự tính lại ngày công cho khoảng punch vừa nhận (MSNV đã có hồ sơ)
    if inserted > 0:
        from app.modules.attendance.engine import to_vn
        from app.modules.attendance.service import recalculate_days

        dates = [
            to_vn(normalize_punch_time(p.punch_time)).date()
            for p in body.punches
            if p.employee_code.strip() in known_codes
        ]
        if dates:
            recalculate_days(db, date_from=min(dates), date_to=max(dates))
            from app.modules.attendance.timesheet import rebuild_timesheets

            for period in {f"{d.year:04d}-{d.month:02d}" for d in dates}:
                rebuild_timesheets(db, period, recalc_days=False)

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
