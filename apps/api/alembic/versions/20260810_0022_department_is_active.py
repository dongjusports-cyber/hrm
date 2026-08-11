"""departments: is_active (đánh dấu bộ phận ngưng dùng, VD Line 1-12 → tái cấu trúc 07/2026)

Revision ID: 20260810_0022
Revises: 20260810_0021
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0022"
down_revision: Union[str, None] = "20260810_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "departments",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("departments", "is_active")
