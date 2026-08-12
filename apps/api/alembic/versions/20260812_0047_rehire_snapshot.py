"""Tái tuyển — snapshot lúc nghỉ + rehire_mode (P3).

Revision ID: 20260812_0047
Revises: 20260811_0046
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision = "20260812_0047"
down_revision = "20260811_0046"
branch_labels = None
depends_on = None

PayloadType = JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("employee_resignations", sa.Column("snapshot_json", PayloadType, nullable=True))
    op.add_column("employee_resignations", sa.Column("rehire_mode", sa.String(20), nullable=True))
    op.add_column("employee_resignations", sa.Column("rehire_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("employee_resignations", "rehire_reason")
    op.drop_column("employee_resignations", "rehire_mode")
    op.drop_column("employee_resignations", "snapshot_json")
