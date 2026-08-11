"""Hạng mục 2.3 — allowance_types -> pay_components (đổi tên, giữ dữ liệu) + 5 cột mới

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.4. Đổi tên bảng, KHÔNG tạo bảng song song — FK của
employee_allowance_assignments.allowance_type_id trỏ theo tên bảng mới.

Revision ID: 20260810_0028
Revises: 20260810_0027
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0028"
down_revision: Union[str, None] = "20260810_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("allowance_types", "pay_components")
    op.add_column(
        "pay_components",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="earning"),
    )
    op.add_column(
        "pay_components",
        sa.Column("affects_si_base", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "pay_components",
        sa.Column("affects_ot_base", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "pay_components",
        sa.Column("affects_pit", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "pay_components",
        sa.Column("proration_rule", sa.String(length=30), nullable=False, server_default="none"),
    )


def downgrade() -> None:
    op.drop_column("pay_components", "proration_rule")
    op.drop_column("pay_components", "affects_pit")
    op.drop_column("pay_components", "affects_ot_base")
    op.drop_column("pay_components", "affects_si_base")
    op.drop_column("pay_components", "kind")
    op.rename_table("pay_components", "allowance_types")
