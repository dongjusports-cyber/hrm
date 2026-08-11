"""Hạng mục 2.7 — roles + role_permissions (21§21.4)

Revision ID: 20260810_0031
Revises: 20260810_0030
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0031"
down_revision: Union[str, None] = "20260810_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_code", sa.String(length=40), nullable=False),
        sa.Column("module_key", sa.String(length=40), nullable=False),
        sa.Column("tab_key", sa.String(length=40), nullable=False, server_default="*"),
        sa.Column("level", sa.String(length=10), nullable=False, server_default="none"),
        sa.ForeignKeyConstraint(["role_code"], ["roles.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_code", "module_key", "tab_key"),
    )
    op.add_column("users", sa.Column("role_code", sa.String(length=40), nullable=True))
    op.create_index("ix_users_role_code", "users", ["role_code"])
    op.create_foreign_key(
        "fk_users_role_code_roles",
        "users",
        "roles",
        ["role_code"],
        ["code"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_role_code_roles", "users", type_="foreignkey")
    op.drop_index("ix_users_role_code", table_name="users")
    op.drop_column("users", "role_code")
    op.drop_table("role_permissions")
    op.drop_table("roles")
