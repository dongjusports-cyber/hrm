"""Hạng mục 3.4 — attendance_days mở rộng (21§21.5)

Revision ID: 20260811_0033
Revises: 20260810_0032
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0033"
down_revision: Union[str, None] = "20260810_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attendance_days", sa.Column("work_shift_id", sa.String(length=20), nullable=True))
    op.add_column("attendance_days", sa.Column("leave_code", sa.String(length=40), nullable=True))
    op.add_column(
        "attendance_days",
        sa.Column("source", sa.String(length=10), nullable=False, server_default="machine"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("night_hours", sa.Numeric(7, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("sunday_hours", sa.Numeric(7, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("holiday_hours", sa.Numeric(7, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("ot_night_hours", sa.Numeric(7, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("segment", sa.String(length=10), nullable=False, server_default="official"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("attendance_days", sa.Column("note", sa.Text(), nullable=False, server_default=""))
    op.add_column("attendance_days", sa.Column("edited_by_user_id", sa.Uuid(), nullable=True))
    op.add_column("attendance_days", sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key(
        "fk_attendance_days_work_shift_id",
        "attendance_days",
        "work_shifts",
        ["work_shift_id"],
        ["code"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_attendance_days_leave_code",
        "attendance_days",
        "leave_types",
        ["leave_code"],
        ["code"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_attendance_days_edited_by_user_id",
        "attendance_days",
        "users",
        ["edited_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_attendance_days_segment", "attendance_days", ["segment"])


def downgrade() -> None:
    op.drop_index("ix_attendance_days_segment", table_name="attendance_days")
    op.drop_constraint("fk_attendance_days_edited_by_user_id", "attendance_days", type_="foreignkey")
    op.drop_constraint("fk_attendance_days_leave_code", "attendance_days", type_="foreignkey")
    op.drop_constraint("fk_attendance_days_work_shift_id", "attendance_days", type_="foreignkey")
    op.drop_column("attendance_days", "edited_at")
    op.drop_column("attendance_days", "edited_by_user_id")
    op.drop_column("attendance_days", "note")
    op.drop_column("attendance_days", "is_locked")
    op.drop_column("attendance_days", "segment")
    op.drop_column("attendance_days", "ot_night_hours")
    op.drop_column("attendance_days", "holiday_hours")
    op.drop_column("attendance_days", "sunday_hours")
    op.drop_column("attendance_days", "night_hours")
    op.drop_column("attendance_days", "source")
    op.drop_column("attendance_days", "leave_code")
    op.drop_column("attendance_days", "work_shift_id")
