"""attendance_days — late/early/ot

Revision ID: 20260809_0006
Revises: 20260809_0005
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0006"
down_revision: Union[str, None] = "20260809_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendance_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("first_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worked_hours", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("late_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ot_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ot_type", sa.String(length=40), nullable=True),
        sa.Column("punch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_workday", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_attendance_day"),
    )
    op.create_index("ix_attendance_days_employee_id", "attendance_days", ["employee_id"])
    op.create_index("ix_attendance_days_work_date", "attendance_days", ["work_date"])


def downgrade() -> None:
    op.drop_index("ix_attendance_days_work_date", table_name="attendance_days")
    op.drop_index("ix_attendance_days_employee_id", table_name="attendance_days")
    op.drop_table("attendance_days")
