"""QA-04 — attendance_days.leave_days (nghỉ nửa ngày = 0.5).

Revision ID: 20260816_0052
Revises: 20260815_0051
Create Date: 2026-08-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0052"
down_revision: Union[str, None] = "20260815_0051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance_days",
        sa.Column(
            "leave_days",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("attendance_days", "leave_days")
