"""Hạng mục 3.5 — timesheet_month_details (21§21.5)

Revision ID: 20260811_0034
Revises: 20260811_0033
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0034"
down_revision: Union[str, None] = "20260811_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "timesheet_month_details",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timesheet_month_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("segment", sa.String(length=10), nullable=False),
        sa.Column("hours", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("days", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["timesheet_month_id"],
            ["timesheet_months.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "timesheet_month_id",
            "category",
            "segment",
            name="uq_timesheet_month_detail_cat_seg",
        ),
    )
    op.create_index(
        "ix_timesheet_month_details_timesheet_month_id",
        "timesheet_month_details",
        ["timesheet_month_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_timesheet_month_details_timesheet_month_id", table_name="timesheet_month_details")
    op.drop_table("timesheet_month_details")
