"""ai_alerts — Lớp A nhắc việc

Revision ID: 20260809_0008
Revises: 20260809_0007
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0008"
down_revision: Union[str, None] = "20260809_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_module", sa.String(length=40), nullable=False, server_default="timekeeping"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("source_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_ref"),
    )
    op.create_index("ix_ai_alerts_rule_key", "ai_alerts", ["rule_key"])
    op.create_index("ix_ai_alerts_user_id", "ai_alerts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_alerts_user_id", table_name="ai_alerts")
    op.drop_index("ix_ai_alerts_rule_key", table_name="ai_alerts")
    op.drop_table("ai_alerts")
