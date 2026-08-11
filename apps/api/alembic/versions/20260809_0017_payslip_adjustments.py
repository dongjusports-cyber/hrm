"""payslip_adjustments — Re-Pay / truy lĩnh / tạm ứng (07§7.5 / 10.3#15)

Revision ID: 20260809_0017
Revises: 20260809_0016
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0017"
down_revision: Union[str, None] = "20260809_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payslip_adjustments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pay_period_id", sa.Uuid(as_uuid=True), sa.ForeignKey("pay_periods.id"), nullable=False),
        sa.Column("employee_id", sa.Uuid(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False, server_default=""),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payslip_adjustments_period", "payslip_adjustments", ["pay_period_id"])
    op.create_index("ix_payslip_adjustments_employee", "payslip_adjustments", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_payslip_adjustments_employee", table_name="payslip_adjustments")
    op.drop_index("ix_payslip_adjustments_period", table_name="payslip_adjustments")
    op.drop_table("payslip_adjustments")
