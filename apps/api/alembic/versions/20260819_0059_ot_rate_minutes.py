"""OT Dongju: phút theo hệ số khung giờ trên attendance_days + timesheet_months.

Revision ID: 20260819_0059
Revises: 20260819_0058
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import JSON

revision: str = "20260819_0059"
down_revision: Union[str, None] = "20260819_0058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attendance_days",
        sa.Column("ot_rate_minutes", JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "timesheet_months",
        sa.Column("ot_hours_by_rate", JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )


def downgrade() -> None:
    op.drop_column("timesheet_months", "ot_hours_by_rate")
    op.drop_column("attendance_days", "ot_rate_minutes")
