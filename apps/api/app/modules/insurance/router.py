"""API Bảo Hiểm Thuế (P6.2) + khai báo BHXH (5.5)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSession
from app.modules.core.models import User
from app.modules.insurance import declarations as decl_svc
from app.modules.insurance import service
from app.modules.insurance.schemas import (
    InsuranceDeclarationBatchExportOut,
    InsuranceDeclarationOut,
    InsuranceDeclarationProposeOut,
    InsuranceDeclarationSubmitBody,
    InsuranceDeclarationSubmitOut,
    InsurancePeriodSummary,
    InsuranceRowOut,
)

router = APIRouter(prefix="/insurance", tags=["insurance"])


def _viewer(user: CurrentUser) -> User:
    service.require_insurance_access(user)
    return user


@router.get("/periods/{period}/summary", response_model=InsurancePeriodSummary)
def get_summary(
    period: str,
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
) -> InsurancePeriodSummary:
    return service.period_summary(db, period)


@router.get("/periods/{period}/rows", response_model=list[InsuranceRowOut])
def get_rows(
    period: str,
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
) -> list[InsuranceRowOut]:
    return service.period_rows(db, period)


# --- 5.5 insurance_declarations ---


@router.get("/declarations", response_model=list[InsuranceDeclarationOut])
def list_declarations(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    effective_month: str | None = Query(default=None),
    status: str | None = Query(default=None),
    declaration_type: str | None = Query(default=None),
) -> list[InsuranceDeclarationOut]:
    return decl_svc.list_declarations(
        db,
        effective_month=effective_month,
        status=status,
        declaration_type=declaration_type,
    )


@router.post("/declarations/propose/{effective_month}", response_model=InsuranceDeclarationProposeOut)
def propose_declarations(
    effective_month: str,
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
) -> InsuranceDeclarationProposeOut:
    return decl_svc.propose_monthly(db, effective_month)


@router.post("/declarations/export", response_model=InsuranceDeclarationBatchExportOut)
def export_declarations_batch(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    effective_month: str = Query(description="YYYY-MM"),
    declaration_ids: list[UUID] | None = Query(default=None),
) -> InsuranceDeclarationBatchExportOut:
    return decl_svc.export_batch(db, effective_month=effective_month, declaration_ids=declaration_ids)


@router.get("/declarations/export/download")
def download_declarations_batch(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    effective_month: str = Query(description="YYYY-MM"),
    declaration_ids: list[UUID] | None = Query(default=None),
) -> Response:
    result = decl_svc.export_batch(db, effective_month=effective_month, declaration_ids=declaration_ids)
    return Response(
        content=result.content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )


@router.post("/declarations/mark-submitted", response_model=InsuranceDeclarationSubmitOut)
def mark_declarations_submitted(
    body: InsuranceDeclarationSubmitBody,
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
) -> InsuranceDeclarationSubmitOut:
    return decl_svc.mark_submitted(
        db,
        effective_month=body.effective_month,
        batch_no=body.batch_no,
        declaration_ids=body.declaration_ids,
    )
