"""payslip confirm_deadline + confirmed_at

Revision ID: 20260809_0011
Revises: 20260809_0010
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0011"
down_revision: Union[str, None] = "20260809_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payslips", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payslips", sa.Column("confirm_deadline", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("payslips", "confirm_deadline")
    op.drop_column("payslips", "confirmed_at")
