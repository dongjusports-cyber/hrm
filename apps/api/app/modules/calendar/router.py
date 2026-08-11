"""API calendar — divisor + holidays + work week (file 08)."""

from datetime import date

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.modules.calendar import service
from app.modules.calendar.schemas import (
    DivisorOut,
    HolidayIn,
    HolidayOut,
    WorkWeekOut,
    WorkWeekUpdate,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/divisor", response_model=DivisorOut)
def get_divisor(
    _user: CurrentUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> DivisorOut:
    return service.compute_divisor(db, year, month)


@router.get("/work-week", response_model=WorkWeekOut)
def get_work_week(_user: CurrentUser, db: DbSession) -> WorkWeekOut:
    return WorkWeekOut.model_validate(service.get_work_week(db))


@router.put("/work-week", response_model=WorkWeekOut)
def put_work_week(body: WorkWeekUpdate, _admin: AdminUser, db: DbSession) -> WorkWeekOut:
    return service.update_work_week(db, body)


@router.get("/holidays", response_model=list[HolidayOut])
def get_holidays(
    _user: CurrentUser,
    db: DbSession,
    year: int | None = Query(default=None, ge=2000, le=2100),
) -> list[HolidayOut]:
    return service.list_holidays(db, year)


@router.post("/holidays", response_model=HolidayOut, status_code=201)
def post_holiday(body: HolidayIn, _admin: AdminUser, db: DbSession) -> HolidayOut:
    return service.add_holiday(db, body)


@router.delete("/holidays/{day}", status_code=204)
def remove_holiday(day: date, _admin: AdminUser, db: DbSession) -> None:
    service.delete_holiday(db, day)
