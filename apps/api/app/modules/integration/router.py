"""API integrations Mitapro + attendance sync (file 08)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header

from app.core.deps import AdminUser, CurrentUser, DbSession, require_module
from app.modules.integration import service
from app.modules.integration.post_ingest import run_post_ingest_recalc
from app.modules.integration.schemas import (
    IntegrationStatusOut,
    MitaproErrorReport,
    MitaproPushRequest,
    MitaproPushResult,
    SyncJobOut,
    SyncJobsListOut,
    SyncRangeRequest,
    UnlinkedPunchesOut,
)

router = APIRouter(tags=["integration"])

TimekeepingUser = Annotated[object, Depends(require_module("timekeeping"))]


def _agent_token(
    x_agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    if x_agent_token:
        return x_agent_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


@router.post("/integrations/mitapro/push", response_model=MitaproPushResult)
def mitapro_push(
    body: MitaproPushRequest,
    db: DbSession,
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Depends(_agent_token)] = None,
) -> MitaproPushResult:
    service.verify_agent_token(token)

    def schedule_recalc(job_id, date_from, date_to, partial, base_message):
        if get_settings().sync_recalc_inline:
            return
        background_tasks.add_task(
            run_post_ingest_recalc,
            job_id,
            date_from=date_from,
            date_to=date_to,
            partial=partial,
            base_message=base_message,
        )

    return service.ingest_punches(
        db,
        body,
        trigger="agent",
        claimed_job_id=body.claimed_job_id,
        on_recalc_scheduled=schedule_recalc,
    )


@router.post("/integrations/mitapro/error", response_model=SyncJobOut)
def mitapro_error(
    body: MitaproErrorReport,
    db: DbSession,
    token: Annotated[str | None, Depends(_agent_token)] = None,
) -> SyncJobOut:
    """Agent báo sync thất bại → sync_jobs + AI alert Admin."""
    service.verify_agent_token(token)
    return service.report_sync_error(db, body.message, agent_name=body.agent_name)


@router.get("/integrations/mitapro/pending", response_model=list[SyncJobOut])
def mitapro_pending(
    db: DbSession,
    token: Annotated[str | None, Depends(_agent_token)] = None,
) -> list[SyncJobOut]:
    """Agent poll nút Đồng bộ ngay."""
    service.verify_agent_token(token)
    return service.list_pending_requests(db)


@router.post("/integrations/mitapro/pending/{job_id}/claim", response_model=SyncJobOut)
def mitapro_claim(
    job_id: UUID,
    db: DbSession,
    token: Annotated[str | None, Depends(_agent_token)] = None,
) -> SyncJobOut:
    service.verify_agent_token(token)
    return service.claim_pending_request(db, job_id)


@router.get("/integrations/status", response_model=IntegrationStatusOut)
def integrations_status(_user: CurrentUser, db: DbSession) -> IntegrationStatusOut:
    return service.integration_status(db)


@router.post("/attendance/sync-now", response_model=SyncJobOut)
def attendance_sync_now(_user: TimekeepingUser, db: DbSession) -> SyncJobOut:
    return service.request_sync_now(db)


@router.post("/attendance/sync-range", response_model=SyncJobOut)
def attendance_sync_range(
    body: SyncRangeRequest, _user: TimekeepingUser, db: DbSession
) -> SyncJobOut:
    """Chạy lại đồng bộ Mitapro cho một khoảng ngày (3.8)."""
    return service.request_sync_range(db, date_from=body.date_from, date_to=body.date_to)


@router.get("/integrations/sync-jobs", response_model=SyncJobsListOut)
def integrations_sync_jobs(
    _user: TimekeepingUser,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> SyncJobsListOut:
    return service.list_sync_jobs(db, limit=limit, offset=offset)


@router.get("/integrations/punches/unlinked", response_model=UnlinkedPunchesOut)
def punches_unlinked(_user: TimekeepingUser, db: DbSession, limit: int = 100) -> UnlinkedPunchesOut:
    """Punch chưa khớp employees.id — chuẩn bị màn 3.8."""
    return service.list_unlinked_punches(db, limit=limit)


@router.post("/integrations/punches/relink")
def punches_relink(_admin: AdminUser, db: DbSession) -> dict:
    """Gắn lại employee_id theo MSNV (chỉ cột liên kết, không sửa giờ chấm gốc)."""
    return service.relink_punches(db)
