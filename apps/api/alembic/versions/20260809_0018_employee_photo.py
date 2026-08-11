"""employees.photo_path — ảnh hồ sơ NV

Revision ID: 20260809_0018
Revises: 20260809_0017
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0018"
down_revision: Union[str, None] = "20260809_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("photo_path", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("employees", "photo_path")
