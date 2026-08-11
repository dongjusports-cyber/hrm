"""Hạng mục 2.4 — work_shifts + team_shift_schedules + teams.default_shift_id

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.5. Chỉ 1 ca hành chính thật (08:00-17:00) nhưng dựng
đủ cột để sau này thêm ca không phải migration lại.

Revision ID: 20260810_0029
Revises: 20260810_0028
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0029"
down_revision: Union[str, None] = "20260810_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_shifts",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("lunch_start", sa.Time(), nullable=True),
        sa.Column("lunch_end", sa.Time(), nullable=True),
        sa.Column("dinner_start", sa.Time(), nullable=True),
        sa.Column("dinner_end", sa.Time(), nullable=True),
        sa.Column("ot_start", sa.Time(), nullable=True),
        sa.Column("night_start", sa.Time(), nullable=True),
        sa.Column("lunch_deduct_hours", sa.Numeric(3, 1), nullable=False, server_default="0"),
        sa.Column("dinner_deduct_hours", sa.Numeric(3, 1), nullable=False, server_default="0"),
        sa.Column("standard_hours", sa.Numeric(3, 1), nullable=False, server_default="8"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "team_shift_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("work_shift_id", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["work_shift_id"], ["work_shifts.code"]),
        sa.UniqueConstraint("team_id", "work_date", name="uq_team_shift_date"),
    )
    op.create_index("ix_team_shift_schedules_team_id", "team_shift_schedules", ["team_id"])
    op.create_index("ix_team_shift_schedules_work_date", "team_shift_schedules", ["work_date"])

    op.add_column("teams", sa.Column("default_shift_id", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "teams_default_shift_id_fkey", "teams", "work_shifts", ["default_shift_id"], ["code"]
    )


def downgrade() -> None:
    op.drop_constraint("teams_default_shift_id_fkey", "teams", type_="foreignkey")
    op.drop_column("teams", "default_shift_id")
    op.drop_index("ix_team_shift_schedules_work_date", table_name="team_shift_schedules")
    op.drop_index("ix_team_shift_schedules_team_id", table_name="team_shift_schedules")
    op.drop_table("team_shift_schedules")
    op.drop_table("work_shifts")
