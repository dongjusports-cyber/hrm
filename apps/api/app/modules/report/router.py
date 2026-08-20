"""API Báo Cáo / KPI + overview (P5.1)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSession
from app.modules.core.excel_filename import attachment_content_disposition, company_excel_filename
from app.modules.core.models import User
from app.modules.report import service, team_kpi, team_kpi_export
from app.modules.report.schemas import (
    KpiDayOut,
    KpiDayPerson,
    KpiMonthOut,
    KpiMonthPerson,
    KpiPeriodOut,
    OverviewOut,
)

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


@router.get("/kpi/day", response_model=KpiDayOut)
def get_kpi_day(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    work_date: date,
) -> KpiDayOut:
    return team_kpi.compute_day(db, work_date)


@router.get("/kpi/day/people", response_model=list[KpiDayPerson])
def get_kpi_day_people(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    work_date: date,
    team_id: Annotated[str | None, Query()] = None,
) -> list[KpiDayPerson]:
    return team_kpi.list_day_people(db, work_date, team_id)


@router.get("/kpi/month-teams", response_model=KpiMonthOut)
def get_kpi_month_teams(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    period: Annotated[str, Query(description="YYYY-MM")],
) -> KpiMonthOut:
    return team_kpi.compute_month(db, period)


@router.get("/kpi/month-teams/people", response_model=list[KpiMonthPerson])
def get_kpi_month_people(
    db: DbSession,
    _user: Annotated[User, Depends(_viewer)],
    period: Annotated[str, Query(description="YYYY-MM")],
    team_id: Annotated[str | None, Query()] = None,
) -> list[KpiMonthPerson]:
    return team_kpi.list_month_people(db, period, team_id)


@router.get("/kpi/export-day")
def export_kpi_day(
    db: DbSession,
    user: Annotated[User, Depends(_viewer)],
    work_date: date,
) -> Response:
    data, filename = team_kpi_export.build_day_xlsx(db, work_date, user_id=user.id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/kpi/export-month")
def export_kpi_month(
    db: DbSession,
    user: Annotated[User, Depends(_viewer)],
    period: Annotated[str, Query(description="YYYY-MM")],
) -> Response:
    data, filename = team_kpi_export.build_month_xlsx(db, period, user_id=user.id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
