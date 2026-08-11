"""Bỏ cột mã quẹt thẻ — công ty dùng vân tay Mitapro, map MSNV/MaChamCong qua Agent.

Revision ID: 20260811_0046
Revises: 20260811_0045
"""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0046"
down_revision = "20260811_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE leave_types SET name = 'Không chấm công' WHERE code = 'NON'")
    op.drop_index("ix_employees_timekeeping_card_no", table_name="employees")
    op.drop_column("employees", "timekeeping_card_no")


def downgrade() -> None:
    op.add_column("employees", sa.Column("timekeeping_card_no", sa.String(40), nullable=True))
    op.create_index("ix_employees_timekeeping_card_no", "employees", ["timekeeping_card_no"])
    op.execute("UPDATE leave_types SET name = 'Không quét thẻ' WHERE code = 'NON'")
