"""payslip_components — mỗi khoản một dòng (4.1)

Revision ID: 20260811_0037
Revises: 20260811_0036
Create Date: 2026-08-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0037"
down_revision: Union[str, None] = "20260811_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payslip_components",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payslip_id", sa.Uuid(), nullable=False),
        sa.Column("component_code", sa.String(length=40), nullable=False),
        sa.Column("segment", sa.String(length=10), nullable=False, server_default="official"),
        sa.Column("seq_no", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("quantity", sa.Numeric(9, 2), nullable=True),
        sa.Column("unit", sa.String(length=10), nullable=True),
        sa.Column("unit_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["component_code"], ["pay_components.code"]),
        sa.ForeignKeyConstraint(["payslip_id"], ["payslips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payslip_id",
            "component_code",
            "segment",
            "seq_no",
            name="uq_payslip_component_line",
        ),
    )
    op.create_index("ix_payslip_components_payslip_id", "payslip_components", ["payslip_id"])
    op.create_index("ix_payslip_components_component_code", "payslip_components", ["component_code"])


def downgrade() -> None:
    op.drop_index("ix_payslip_components_component_code", table_name="payslip_components")
    op.drop_index("ix_payslip_components_payslip_id", table_name="payslip_components")
    op.drop_table("payslip_components")
