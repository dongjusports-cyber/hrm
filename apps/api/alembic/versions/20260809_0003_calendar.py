"""calendar holidays + work_week_rules

Revision ID: 20260809_0003
Revises: 20260809_0002
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0003"
down_revision: Union[str, None] = "20260809_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("date"),
    )
    op.create_table(
        "work_week_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_weekdays", sa.JSON(), nullable=False),
        sa.Column("morning_start", sa.Time(), nullable=False),
        sa.Column("morning_end", sa.Time(), nullable=False),
        sa.Column("afternoon_start", sa.Time(), nullable=False),
        sa.Column("afternoon_end", sa.Time(), nullable=False),
        sa.Column("grace_late_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("work_week_rules")
    op.drop_table("holidays")
