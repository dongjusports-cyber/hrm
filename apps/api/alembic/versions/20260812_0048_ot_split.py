"""OT sổ / OT ngoài — attendance_days + timesheet_months.

Revision ID: 20260812_0048
Revises: 20260812_0047
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0048"
down_revision: Union[str, None] = "20260812_0047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance_days",
        sa.Column("ot_on_books_minutes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "attendance_days",
        sa.Column("ot_external_minutes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "timesheet_months",
        sa.Column("ot_hours_external", sa.Numeric(8, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("timesheet_months", "ot_hours_external")
    op.drop_column("attendance_days", "ot_external_minutes")
    op.drop_column("attendance_days", "ot_on_books_minutes")
