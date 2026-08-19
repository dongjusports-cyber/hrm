"""Seed ca làm việc (`work_shifts`, hạng mục 2.4, 21§21.5).

ADMIN hành chính 08–17. CLEANER tạp vụ hết ca 16:00, OT từ 17:00.
COOKER nấu ăn (tổ code 05, MSNV 1581 / 1733): công 08–17 + OT sáng 6–8 nếu bấm trước 6:00.
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.attendance.models import WorkShift
from app.modules.mdm.models import Team

ADMIN_SHIFT_CODE = "ADMIN"
CLEANER_SHIFT_CODE = "CLEANER"
COOKER_SHIFT_CODE = "COOKER"
# Tổ tạp vụ — teams.code = "02" (bộ phận HR & Admin).
CLEANER_TEAM_CODE = "02"
# Tổ nấu ăn — teams.code = "05", hiện 1581 / 1733.
COOKER_TEAM_CODE = "05"


def seed_work_shifts(db: Session) -> None:
    """Seed ca ADMIN + CLEANER + COOKER (idempotent)."""
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
    changed_cooker = _upsert_shift(
        db,
        COOKER_SHIFT_CODE,
        name="Ca nấu ăn (công 08:00–17:00, OT sáng 06:00–08:00)",
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
    if changed_admin or changed_cleaner or changed_cooker:
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


def _assign_team_shift(db: Session, team_code: str, shift_code: str) -> int:
    """Gán ca cho tổ theo code. Chỉ ghi nếu đang NULL/ADMIN — không đè ca HR set tay."""
    teams = db.query(Team).filter(Team.code == team_code).all()
    n = 0
    for t in teams:
        if t.default_shift_id in (None, ADMIN_SHIFT_CODE):
            t.default_shift_id = shift_code
            n += 1
    return n


def assign_default_shift_to_teams(db: Session) -> int:
    """Gán ca hành chính làm mặc định cho tổ CHƯA có default_shift_id — idempotent.
    Tổ tạp vụ (02) → CLEANER. Tổ nấu ăn (05) → COOKER."""
    seed_work_shifts(db)
    rows = db.query(Team).filter(Team.default_shift_id.is_(None)).all()
    for t in rows:
        t.default_shift_id = ADMIN_SHIFT_CODE
    extra = _assign_team_shift(db, CLEANER_TEAM_CODE, CLEANER_SHIFT_CODE)
    extra += _assign_team_shift(db, COOKER_TEAM_CODE, COOKER_SHIFT_CODE)
    if rows or extra:
        db.commit()
    return len(rows)
