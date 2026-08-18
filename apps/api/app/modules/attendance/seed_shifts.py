"""Seed ca làm việc (`work_shifts`, hạng mục 2.4, 21§21.5) — thực tế công ty chỉ dùng
1 ca hành chính. HR thêm ca khác qua Admin (2.8) khi cần, không sửa code."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.attendance.models import WorkShift
from app.modules.mdm.models import Team

ADMIN_SHIFT_CODE = "ADMIN"
CLEANER_SHIFT_CODE = "CLEANER"
# Tổ tạp vụ — teams.code = "02" (bộ phận HR & Admin), tra theo CODE không hard-code id.
CLEANER_TEAM_CODE = "02"


def seed_work_shifts(db: Session) -> None:
    """Seed ca ADMIN + CLEANER (idempotent). CLEANER hết ca 16:00, OT từ 17:00.

    Nghỉ cơm 17:00–17:30: vân tay trong khung không tính nếu còn bấm sau 17:30.
    """
    changed_admin = _upsert_shift(
        db,
        ADMIN_SHIFT_CODE,
        name="Hành chính (08:00–17:00)",
        start_time=time(8, 0),
        end_time=time(17, 0),
        lunch_start=time(12, 0),
        lunch_end=time(13, 0),
        dinner_start=time(17, 0),
        dinner_end=time(17, 30),
        ot_start=time(17, 0),
        night_start=time(22, 0),
        lunch_deduct_hours=Decimal("1.0"),
        dinner_deduct_hours=Decimal("0"),
        standard_hours=Decimal("8.0"),
    )
    changed_cleaner = _upsert_shift(
        db,
        CLEANER_SHIFT_CODE,
        name="Ca tạp vụ (07:00–16:00)",
        start_time=time(7, 0),
        end_time=time(16, 0),
        lunch_start=time(12, 0),
        lunch_end=time(13, 0),
        dinner_start=time(17, 0),
        dinner_end=time(17, 30),
        ot_start=time(17, 0),
        night_start=time(22, 0),
        lunch_deduct_hours=Decimal("1.0"),
        dinner_deduct_hours=Decimal("0"),
        standard_hours=Decimal("8.0"),
    )
    if changed_admin or changed_cleaner:
        db.commit()


def _upsert_shift(db: Session, code: str, **fields: object) -> bool:
    row = db.get(WorkShift, code)
    if row is None:
        db.add(WorkShift(code=code, **fields))
        return True
    changed = False
    for key, val in fields.items():
        if getattr(row, key) != val:
            setattr(row, key, val)
            changed = True
    return changed


def _assign_cleaner_team(db: Session) -> int:
    """Gán ca CLEANER cho tổ tạp vụ (code 02). Idempotent, chỉ gán nếu đang NULL/ADMIN
    — không đè ca HR đã set tay. Tra theo teams.code, không hard-code id."""
    teams = db.query(Team).filter(Team.code == CLEANER_TEAM_CODE).all()
    n = 0
    for t in teams:
        if t.default_shift_id in (None, ADMIN_SHIFT_CODE):
            t.default_shift_id = CLEANER_SHIFT_CODE
            n += 1
    return n


def assign_default_shift_to_teams(db: Session) -> int:
    """Gán ca hành chính làm mặc định cho tổ CHƯA có default_shift_id — idempotent,
    không ghi đè tổ đã được gán ca khác qua Admin. Tổ tạp vụ (code 02) → ca CLEANER."""
    seed_work_shifts(db)
    rows = db.query(Team).filter(Team.default_shift_id.is_(None)).all()
    for t in rows:
        t.default_shift_id = ADMIN_SHIFT_CODE
    cleaner_assigned = _assign_cleaner_team(db)
    if rows or cleaner_assigned:
        db.commit()
    return len(rows)
