"""Chấm công điện thoại — cấu hình allowlist + GPS.

Revision ID: 20260817_0053
Revises: 20260816_0052
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0053"
down_revision: Union[str, None] = "20260816_0052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mobile_punch_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="allowlist"),
        sa.Column("department_codes", sa.JSON(), nullable=False),
        sa.Column("extra_msnv", sa.JSON(), nullable=False),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lng", sa.Float(), nullable=True),
        sa.Column("gps_radius_m", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("require_photo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mobile_punch_settings")
