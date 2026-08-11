"""sync_jobs — khoảng ngày chạy lại (3.8)

Revision ID: 20260811_0036
Revises: 20260811_0035
Create Date: 2026-08-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0036"
down_revision: Union[str, None] = "20260811_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sync_jobs", sa.Column("sync_date_from", sa.Date(), nullable=True))
    op.add_column("sync_jobs", sa.Column("sync_date_to", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("sync_jobs", "sync_date_to")
    op.drop_column("sync_jobs", "sync_date_from")
