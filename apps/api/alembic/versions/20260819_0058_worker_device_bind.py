"""Worker: khóa 1 MSNV trên 1 điện thoại.

Revision ID: 20260819_0058
Revises: 20260819_0057
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0058"
down_revision: Union[str, None] = "20260819_0057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("worker_device_id", sa.String(length=64), nullable=True))
    op.create_index("uq_users_worker_device_id", "users", ["worker_device_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_worker_device_id", table_name="users")
    op.drop_column("users", "worker_device_id")
