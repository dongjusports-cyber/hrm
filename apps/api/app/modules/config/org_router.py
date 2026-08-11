"""Admin — cây tổ chức (5.6 minimal)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

from app.core.deps import AdminUser, DbSession
from app.modules.attendance.shifts_service import set_team_default_shift
from app.modules.mdm.models import Department, Job, Position, Team

router = APIRouter(prefix="/config/org", tags=["config", "org"])


class OrgSummaryOut(BaseModel):
    departments: int
    teams: int
    positions: int
    jobs: int
    active_departments: int
    active_teams: int


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    name_local: str | None = None
    level: int | None = None
    is_management: bool
    sort_order: int
    is_active: bool


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    name_local: str | None = None
    is_hazardous: bool
    sort_order: int
    is_active: bool


class TeamAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    name_local: str | None = None
    department_id: UUID
    department_code: str | None = None
    department_name: str | None = None
    default_shift_id: str | None = None
    is_active: bool


class TeamDefaultShiftPatch(BaseModel):
    default_shift_id: str = Field(min_length=1, max_length=20)


@router.get("/summary", response_model=OrgSummaryOut)
def org_summary(_admin: AdminUser, db: DbSession) -> OrgSummaryOut:
    depts = db.query(Department).all()
    teams = db.query(Team).all()
    return OrgSummaryOut(
        departments=len(depts),
        teams=len(teams),
        positions=db.query(Position).count(),
        jobs=db.query(Job).count(),
        active_departments=sum(1 for d in depts if d.is_active),
        active_teams=sum(1 for t in teams if t.is_active),
    )


@router.get("/positions", response_model=list[PositionOut])
def org_positions(_admin: AdminUser, db: DbSession) -> list[PositionOut]:
    rows = db.query(Position).order_by(Position.sort_order.asc(), Position.code.asc()).all()
    return [PositionOut.model_validate(r) for r in rows]


@router.get("/jobs", response_model=list[JobOut])
def org_jobs(_admin: AdminUser, db: DbSession) -> list[JobOut]:
    rows = db.query(Job).order_by(Job.sort_order.asc(), Job.code.asc()).all()
    return [JobOut.model_validate(r) for r in rows]


@router.get("/teams", response_model=list[TeamAdminOut])
def org_teams(_admin: AdminUser, db: DbSession) -> list[TeamAdminOut]:
    rows = (
        db.query(Team, Department)
        .join(Department, Department.id == Team.department_id)
        .order_by(Department.code.asc(), Team.code.asc())
        .all()
    )
    out: list[TeamAdminOut] = []
    for team, dept in rows:
        out.append(
            TeamAdminOut(
                id=team.id,
                code=team.code,
                name=team.name,
                name_local=team.name_local,
                department_id=team.department_id,
                department_code=dept.code,
                department_name=dept.name,
                default_shift_id=team.default_shift_id,
                is_active=team.is_active,
            )
        )
    return out


@router.patch("/teams/{team_id}/default-shift", response_model=TeamAdminOut)
def patch_team_default_shift(
    team_id: UUID, body: TeamDefaultShiftPatch, admin: AdminUser, db: DbSession
) -> TeamAdminOut:
    """Gán ca mặc định cho tổ (2.4)."""
    team = set_team_default_shift(db, team_id, body.default_shift_id, admin)
    dept = db.get(Department, team.department_id)
    return TeamAdminOut(
        id=team.id,
        code=team.code,
        name=team.name,
        name_local=team.name_local,
        department_id=team.department_id,
        department_code=dept.code if dept else None,
        department_name=dept.name if dept else None,
        default_shift_id=team.default_shift_id,
        is_active=team.is_active,
    )
