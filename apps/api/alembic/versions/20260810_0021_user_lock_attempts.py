"""users: failed_attempts + is_locked (khóa vĩnh viễn sau 3 lần sai)

Revision ID: 20260810_0021
Revises: 20260809_0020
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0021"
down_revision: Union[str, None] = "20260809_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # Đồng bộ từ cột cũ (nếu có)
    op.execute(
        """
        UPDATE users
        SET failed_attempts = COALESCE(failed_login_count, 0),
            is_locked = CASE
                WHEN locked_until IS NOT NULL AND locked_until > NOW() THEN true
                ELSE false
            END
        """
    )


def downgrade() -> None:
    op.drop_column("users", "is_locked")
    op.drop_column("users", "failed_attempts")
