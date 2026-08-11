"""Seed ca làm việc (`work_shifts`, hạng mục 2.4, 21§21.5) — thực tế công ty chỉ dùng
1 ca hành chính. HR thêm ca khác qua Admin (2.8) khi cần, không sửa code."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.attendance.models import WorkShift
from app.modules.mdm.models import Team

ADMIN_SHIFT_CODE = "ADMIN"


def seed_work_shifts(db: Session) -> None:
    if db.get(WorkShift, ADMIN_SHIFT_CODE) is None:
        db.add(
            WorkShift(
                code=ADMIN_SHIFT_CODE,
                name="Hành chính (08:00–17:00)",
                start_time=time(8, 0),
                end_time=time(17, 0),
                lunch_start=time(12, 0),
                lunch_end=time(13, 0),
                dinner_start=None,
                dinner_end=None,
                ot_start=time(17, 0),
                night_start=time(22, 0),  # mốc ca đêm theo luật LĐ VN (22:00–06:00)
                lunch_deduct_hours=Decimal("1.0"),
                dinner_deduct_hours=Decimal("0"),
                standard_hours=Decimal("8.0"),
            )
        )
        db.commit()


def assign_default_shift_to_teams(db: Session) -> int:
    """Gán ca hành chính làm mặc định cho tổ CHƯA có default_shift_id — idempotent,
    không ghi đè tổ đã được gán ca khác qua Admin."""
    seed_work_shifts(db)
    rows = db.query(Team).filter(Team.default_shift_id.is_(None)).all()
    for t in rows:
        t.default_shift_id = ADMIN_SHIFT_CODE
    if rows:
        db.commit()
    return len(rows)
