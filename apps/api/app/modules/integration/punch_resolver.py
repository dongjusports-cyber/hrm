"""Phân giải MSNV / MaChamCong (vân tay Mitapro) → employees.id lúc nạp punch (3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from sqlalchemy import not_

from app.modules.integration.models import AttendancePunch
from app.modules.mdm.models import Employee

# MSNV 200* — bảo vệ đi tuần bấm máy Mitapro; không phải nhân viên HRM.
PATROL_GUARD_CODE_PREFIX = "200"


def is_patrol_guard_code(employee_code: str) -> bool:
    code = employee_code.strip()
    return bool(code) and code.startswith(PATROL_GUARD_CODE_PREFIX)


def exclude_patrol_guard_punches(query):
    """Loại punch bảo vệ tuần khỏi thống kê / danh sách chưa khớp."""
    return query.filter(not_(AttendancePunch.employee_code.like(f"{PATROL_GUARD_CODE_PREFIX}%")))


@dataclass(frozen=True)
class EmployeeResolveMaps:
    by_code: dict[str, UUID]
    by_ma_cham: dict[str, UUID]


def build_employee_resolve_maps(db: Session) -> EmployeeResolveMaps:
    rows = (
        db.query(Employee.id, Employee.employee_code)
        .filter(Employee.deleted_at.is_(None))
        .all()
    )
    by_code = {code.strip(): eid for eid, code in rows if code}
    return EmployeeResolveMaps(by_code=by_code, by_ma_cham={})


def resolve_employee_id(
    maps: EmployeeResolveMaps,
    *,
    employee_code: str,
    ma_cham_cong: str | None = None,
) -> UUID | None:
    code = employee_code.strip()
    if code and code in maps.by_code:
        return maps.by_code[code]
    if ma_cham_cong:
        mc = ma_cham_cong.strip()
        if mc in maps.by_ma_cham:
            return maps.by_ma_cham[mc]
    return None


def normalize_direction(raw: str | None) -> str | None:
    if not raw:
        return None
    v = raw.strip().upper()
    if v in ("IN", "OUT"):
        return v
    if v in ("I", "1", "VÀO", "VAO"):
        return "IN"
    if v in ("O", "0", "RA"):
        return "OUT"
    return None


def direction_from_punch_in(explicit: str | None, raw: dict | None) -> str | None:
    d = normalize_direction(explicit)
    if d:
        return d
    if raw:
        for key in ("direction", "in_out", "InOut", "io"):
            if key in raw and raw[key] is not None:
                d2 = normalize_direction(str(raw[key]))
                if d2:
                    return d2
    return None


def backfill_unlinked_punches(db: Session, *, employee_codes: set[str] | None = None) -> int:
    """Gắn lại employee_id cho punch cũ khi HR vừa thêm NV."""
    from app.modules.integration.models import AttendancePunch

    maps = build_employee_resolve_maps(db)
    q = db.query(AttendancePunch).filter(AttendancePunch.employee_id.is_(None))
    if employee_codes:
        codes = {c.strip() for c in employee_codes}
        q = q.filter(AttendancePunch.employee_code.in_(codes))
    updated = 0
    for row in q.limit(5000).all():
        eid = resolve_employee_id(maps, employee_code=row.employee_code, ma_cham_cong=row.ma_cham_cong)
        if eid:
            row.employee_id = eid
            updated += 1
    if updated:
        db.commit()
    return updated
