"""API Báo Cáo / KPI + overview (P5.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSession
from app.modules.core.excel_filename import attachment_content_disposition, company_excel_filename
from app.modules.core.models import User
from app.modules.report import service
from app.modules.report.schemas import KpiPeriodOut, OverviewOut

router = APIRouter(prefix="/reports", tags=["report"])


def _viewer(user: CurrentUser) -> User:
    service.require_report_access(user)
    return user


@router.get("/kpi", response_model=KpiPeriodOut)
def get_kpi(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    period: Annotated[str, Query(description="YYYY-MM")],
) -> KpiPeriodOut:
    return service.compute_kpi(db, period)


@router.get("/overview", response_model=OverviewOut)
def get_overview(
    db: DbSession,
    user: Annotated[User, Depends(_viewer)],
    period: Annotated[str, Query(description="YYYY-MM")],
) -> OverviewOut:
    return service.overview(db, period, user=user)


@router.get("/kpi/export")
def export_kpi(
    db: DbSession,
    user: Annotated[User, Depends(_viewer)],
    period: Annotated[str, Query(description="YYYY-MM")],
) -> Response:
    data = service.export_kpi_xlsx(db, period, user_id=user.id)
    filename = company_excel_filename("KPI", period=period)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": attachment_content_disposition(filename)},
    )
