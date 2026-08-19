"""Cờ chu kỳ trên ngày công — HR tích, danh sách/Excel cuối tháng.

Revision ID: 20260819_0057
Revises: 20260818_0056
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0057"
down_revision: Union[str, None] = "20260818_0056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance_days",
        sa.Column(
            "cycle_leave",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("attendance_days", "cycle_leave")
