"""employees pit_enrolled + tax_dependent_count (P6.2)

Revision ID: 20260809_0016
Revises: 20260809_0015
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0016"
down_revision: Union[str, None] = "20260809_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("pit_enrolled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "employees",
        sa.Column(
            "tax_dependent_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "tax_dependent_count")
    op.drop_column("employees", "pit_enrolled")
