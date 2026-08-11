"""Hạng mục 2.2 — leave_types mở rộng (6 cột mới, đủ 14 mã theo 22§22.6)

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.4. pay_ratio_percent NULL cho phép — riêng PER
("Nghỉ có phép") GenusSuite bỏ trống, buộc HR khai qua Admin (N4), không đoán.

Revision ID: 20260810_0027
Revises: 20260810_0026
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0027"
down_revision: Union[str, None] = "20260810_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leave_types", sa.Column("pay_ratio_percent", sa.Integer(), nullable=True))
    op.add_column(
        "leave_types",
        sa.Column("paid_by_si", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "leave_types",
        sa.Column("affects_attendance_bonus", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "leave_types",
        sa.Column("counts_as_worked_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "leave_types",
        sa.Column("requires_document", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("leave_types", sa.Column("max_days_per_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("leave_types", "max_days_per_year")
    op.drop_column("leave_types", "requires_document")
    op.drop_column("leave_types", "counts_as_worked_day")
    op.drop_column("leave_types", "affects_attendance_bonus")
    op.drop_column("leave_types", "paid_by_si")
    op.drop_column("leave_types", "pay_ratio_percent")
