"""attendance punches + sync_jobs

Revision ID: 20260809_0005
Revises: 20260809_0004
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0005"
down_revision: Union[str, None] = "20260809_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("records_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="mitapro"),
        sa.Column("trigger", sa.String(length=40), nullable=False, server_default="agent"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "attendance_punches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_code", sa.String(length=40), nullable=False),
        sa.Column("punch_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("ma_cham_cong", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code", "punch_time", name="uq_punch_employee_time"),
    )
    op.create_index("ix_attendance_punches_employee_code", "attendance_punches", ["employee_code"])
    op.create_index("ix_attendance_punches_punch_time", "attendance_punches", ["punch_time"])


def downgrade() -> None:
    op.drop_index("ix_attendance_punches_punch_time", table_name="attendance_punches")
    op.drop_index("ix_attendance_punches_employee_code", table_name="attendance_punches")
    op.drop_table("attendance_punches")
    op.drop_table("sync_jobs")
