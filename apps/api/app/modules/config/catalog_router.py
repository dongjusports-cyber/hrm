"""Admin › Danh mục (2.8) — chỉ Admin."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DbSession
from app.modules.config import catalog_service
from app.modules.config.catalog_schemas import (
    LeaveTypeAdminCreate,
    LeaveTypeAdminOut,
    LeaveTypeAdminUpdate,
    LookupValueAdminCreate,
    LookupValueAdminUpdate,
    PayComponentAdminCreate,
    PayComponentAdminOut,
    PayComponentAdminUpdate,
)
from app.modules.attendance.schemas import (
    TeamEffectiveShiftOut,
    TeamShiftScheduleCreate,
    TeamShiftScheduleOut,
    WorkShiftOut,
)
from app.modules.attendance.shifts_service import (
    get_effective_shift,
    list_team_schedules,
    list_work_shifts,
    upsert_team_schedule,
)
from app.modules.audit.service import write_audit
from app.modules.mdm.schemas import LookupValueOut

router = APIRouter(prefix="/config/catalog", tags=["config", "catalog"])


@router.get("/leave-types", response_model=list[LeaveTypeAdminOut])
def admin_list_leave_types(_admin: AdminUser, db: DbSession) -> list[LeaveTypeAdminOut]:
    return catalog_service.list_leave_types_admin(db)


@router.post("/leave-types", response_model=LeaveTypeAdminOut, status_code=201)
def admin_create_leave_type(
    body: LeaveTypeAdminCreate, admin: AdminUser, db: DbSession
) -> LeaveTypeAdminOut:
    return catalog_service.create_leave_type(db, body, admin)


@router.put("/leave-types/{code}", response_model=LeaveTypeAdminOut)
def admin_update_leave_type(
    code: str, body: LeaveTypeAdminUpdate, admin: AdminUser, db: DbSession
) -> LeaveTypeAdminOut:
    return catalog_service.update_leave_type(db, code, body, admin)


@router.get("/pay-components", response_model=list[PayComponentAdminOut])
def admin_list_pay_components(_admin: AdminUser, db: DbSession) -> list[PayComponentAdminOut]:
    return catalog_service.list_pay_components_admin(db)


@router.post("/pay-components", response_model=PayComponentAdminOut, status_code=201)
def admin_create_pay_component(
    body: PayComponentAdminCreate, admin: AdminUser, db: DbSession
) -> PayComponentAdminOut:
    return catalog_service.create_pay_component(db, body, admin)


@router.put("/pay-components/{code}", response_model=PayComponentAdminOut)
def admin_update_pay_component(
    code: str, body: PayComponentAdminUpdate, admin: AdminUser, db: DbSession
) -> PayComponentAdminOut:
    return catalog_service.update_pay_component(db, code, body, admin)


@router.get("/lookup-values", response_model=list[LookupValueOut])
def admin_list_lookup(
    _admin: AdminUser,
    db: DbSession,
    group_code: str | None = Query(default=None),
) -> list[LookupValueOut]:
    return catalog_service.list_lookup_admin(db, group_code)


@router.post("/lookup-values", response_model=LookupValueOut, status_code=201)
def admin_create_lookup(
    body: LookupValueAdminCreate, admin: AdminUser, db: DbSession
) -> LookupValueOut:
    return catalog_service.create_lookup(db, body, admin)


@router.put("/lookup-values/{lookup_id}", response_model=LookupValueOut)
def admin_update_lookup(
    lookup_id: UUID, body: LookupValueAdminUpdate, admin: AdminUser, db: DbSession
) -> LookupValueOut:
    return catalog_service.update_lookup(db, lookup_id, body, admin)


@router.get("/work-shifts", response_model=list[WorkShiftOut])
def admin_list_work_shifts(_admin: AdminUser, db: DbSession) -> list[WorkShiftOut]:
    """Ca làm việc — Admin danh mục (5.6)."""
    return list_work_shifts(db)


@router.get("/team-shift-schedules", response_model=list[TeamShiftScheduleOut])
def admin_list_team_shift_schedules(
    _admin: AdminUser,
    db: DbSession,
    team_id: UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[TeamShiftScheduleOut]:
    """Xếp ca theo ngày — override ca mặc định của tổ (2.4)."""
    return list_team_schedules(db, team_id=team_id, date_from=date_from, date_to=date_to)


@router.post("/team-shift-schedules", response_model=TeamShiftScheduleOut, status_code=201)
def admin_upsert_team_shift_schedule(
    body: TeamShiftScheduleCreate, admin: AdminUser, db: DbSession
) -> TeamShiftScheduleOut:
    result = upsert_team_schedule(db, body)
    write_audit(
        db,
        actor=admin,
        action="team_shift_schedule.upsert",
        entity_type="team_shift_schedule",
        entity_id=str(result.id),
        summary=f"Xếp ca {result.work_shift_id} cho tổ {result.team_code} ngày {result.work_date}",
        meta={
            "team_code": result.team_code,
            "work_date": str(result.work_date),
            "work_shift_id": result.work_shift_id,
        },
    )
    return result


@router.get("/team-shift-schedules/effective", response_model=TeamEffectiveShiftOut)
def admin_effective_team_shift(
    _admin: AdminUser,
    db: DbSession,
    team_id: UUID = Query(...),
    work_date: date = Query(...),
) -> TeamEffectiveShiftOut:
    return get_effective_shift(db, team_id, work_date)
