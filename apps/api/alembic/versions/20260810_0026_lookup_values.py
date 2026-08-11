"""Hạng mục 2.1 — bảng lookup_values (danh mục phẳng, không quy tắc)

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.4. Dân tộc, tôn giáo, quốc tịch, nơi sinh, nơi cấp CCCD,
trình độ — KHÔNG dùng cho danh mục có quy tắc (loại nghỉ, chức vụ...), những bảng đó đã có
riêng hoặc sẽ có riêng, không lặp lại sai lầm TCO_ABCODE của GenusSuite.

Revision ID: 20260810_0026
Revises: 20260810_0025
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0026"
down_revision: Union[str, None] = "20260810_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lookup_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_code", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_local", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_code", "code", name="uq_lookup_values_group_code"),
    )
    op.create_index("ix_lookup_values_group_code", "lookup_values", ["group_code"])


def downgrade() -> None:
    op.drop_index("ix_lookup_values_group_code", table_name="lookup_values")
    op.drop_table("lookup_values")
