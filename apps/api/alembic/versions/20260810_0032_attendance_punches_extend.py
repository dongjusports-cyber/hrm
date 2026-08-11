"""Hạng mục 3.1 — attendance_punches + employee_id, direction, sync_job_id

Revision ID: 20260810_0032
Revises: 20260810_0031
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0032"
down_revision: Union[str, None] = "20260810_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("attendance_punches", sa.Column("employee_id", sa.Uuid(), nullable=True))
    op.add_column("attendance_punches", sa.Column("direction", sa.String(length=3), nullable=True))
    op.add_column("attendance_punches", sa.Column("sync_job_id", sa.Uuid(), nullable=True))
    op.create_index("ix_attendance_punches_employee_id", "attendance_punches", ["employee_id"])
    op.create_index("ix_attendance_punches_sync_job_id", "attendance_punches", ["sync_job_id"])
    op.create_foreign_key(
        "fk_attendance_punches_employee_id",
        "attendance_punches",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_attendance_punches_sync_job_id",
        "attendance_punches",
        "sync_jobs",
        ["sync_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE attendance_punches
            SET employee_id = (
                SELECT e.id FROM employees e
                WHERE e.employee_code = attendance_punches.employee_code
                  AND e.deleted_at IS NULL
                LIMIT 1
            )
            WHERE employee_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_attendance_punches_sync_job_id", "attendance_punches", type_="foreignkey")
    op.drop_constraint("fk_attendance_punches_employee_id", "attendance_punches", type_="foreignkey")
    op.drop_index("ix_attendance_punches_sync_job_id", table_name="attendance_punches")
    op.drop_index("ix_attendance_punches_employee_id", table_name="attendance_punches")
    op.drop_column("attendance_punches", "sync_job_id")
    op.drop_column("attendance_punches", "direction")
    op.drop_column("attendance_punches", "employee_id")
