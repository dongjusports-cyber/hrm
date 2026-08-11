"""Ca làm việc + xếp ca theo Tổ (21§21.5, hạng mục 2.4)."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.attendance.models import TeamShiftSchedule, WorkShift
from app.modules.attendance.schemas import (
    TeamEffectiveShiftOut,
    TeamShiftScheduleCreate,
    TeamShiftScheduleOut,
    WorkShiftOut,
)
from app.modules.attendance.seed_shifts import assign_default_shift_to_teams, seed_work_shifts
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.mdm.models import Team


def list_work_shifts(db: Session) -> list[WorkShiftOut]:
    seed_work_shifts(db)
    rows = db.query(WorkShift).filter(WorkShift.is_active.is_(True)).order_by(WorkShift.code.asc()).all()
    return [WorkShiftOut.model_validate(r) for r in rows]


def upsert_team_schedule(db: Session, body: TeamShiftScheduleCreate) -> TeamShiftScheduleOut:
    """Xếp ca cho MỘT tổ tại MỘT ngày cụ thể — override default_shift_id (23§, N4: HR tự làm,
    không cần lập trình viên khi chỉ đổi ca cho một ngày)."""
    team = db.get(Team, body.team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy tổ.")
    shift = db.get(WorkShift, body.work_shift_id.strip().upper())
    if shift is None:
        raise HTTPException(
            status_code=400, detail=f"Trợ Lý AI: không tìm thấy ca làm việc '{body.work_shift_id}'."
        )
    row = (
        db.query(TeamShiftSchedule)
        .filter(TeamShiftSchedule.team_id == body.team_id, TeamShiftSchedule.work_date == body.work_date)
        .one_or_none()
    )
    if row is None:
        row = TeamShiftSchedule(team_id=body.team_id, work_date=body.work_date)
        db.add(row)
    row.work_shift_id = shift.code
    row.note = body.note
    db.commit()
    db.refresh(row)
    return TeamShiftScheduleOut(
        id=row.id,
        team_id=row.team_id,
        team_code=team.code,
        work_date=row.work_date,
        work_shift_id=row.work_shift_id,
        note=row.note,
    )


def list_team_schedules(
    db: Session,
    *,
    team_id=None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[TeamShiftScheduleOut]:
    q = db.query(TeamShiftSchedule, Team).join(Team, Team.id == TeamShiftSchedule.team_id)
    if team_id:
        q = q.filter(TeamShiftSchedule.team_id == team_id)
    if date_from:
        q = q.filter(TeamShiftSchedule.work_date >= date_from)
    if date_to:
        q = q.filter(TeamShiftSchedule.work_date <= date_to)
    q = q.order_by(TeamShiftSchedule.work_date.asc())
    return [
        TeamShiftScheduleOut(
            id=row.id,
            team_id=row.team_id,
            team_code=team.code,
            work_date=row.work_date,
            work_shift_id=row.work_shift_id,
            note=row.note,
        )
        for row, team in q.all()
    ]


def get_effective_shift(db: Session, team_id, work_date: date) -> TeamEffectiveShiftOut:
    """Ca thật áp dụng cho Tổ tại 1 ngày — override (team_shift_schedules) trước, rồi mới
    rơi về default_shift_id của Tổ. Gán mặc định ADMIN cho tổ nào chưa có (idempotent)."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy tổ.")
    assign_default_shift_to_teams(db)
    db.refresh(team)

    override = (
        db.query(TeamShiftSchedule)
        .filter(TeamShiftSchedule.team_id == team_id, TeamShiftSchedule.work_date == work_date)
        .one_or_none()
    )
    if override is not None:
        return TeamEffectiveShiftOut(
            team_id=team.id,
            team_code=team.code,
            work_date=work_date,
            work_shift_id=override.work_shift_id,
            source="override",
        )
    if team.default_shift_id:
        return TeamEffectiveShiftOut(
            team_id=team.id,
            team_code=team.code,
            work_date=work_date,
            work_shift_id=team.default_shift_id,
            source="team_default",
        )
    return TeamEffectiveShiftOut(
        team_id=team.id, team_code=team.code, work_date=work_date, work_shift_id=None, source="none"
    )


def set_team_default_shift(db: Session, team_id, work_shift_id: str, actor: User) -> Team:
    """Gán ca mặc định cho tổ (2.4 — HR không cần dev khi chỉ đổi ca mặc định)."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy tổ.")
    code = work_shift_id.strip().upper()
    shift = db.get(WorkShift, code)
    if shift is None:
        raise HTTPException(
            status_code=400, detail=f"Trợ Lý AI: không tìm thấy ca làm việc '{code}'."
        )
    before = team.default_shift_id
    team.default_shift_id = code
    db.commit()
    db.refresh(team)
    write_audit(
        db,
        actor=actor,
        action="team.default_shift",
        entity_type="team",
        entity_id=str(team.id),
        summary=f"Đổi ca mặc định tổ {team.code}: {before or '—'} → {code}",
        meta={"before": before, "after": code},
    )
    return team
