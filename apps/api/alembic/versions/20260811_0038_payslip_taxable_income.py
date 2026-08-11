"""4.6 — payslips.taxable_income (22§22.10)."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0038"
down_revision = "20260811_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payslips",
        sa.Column("taxable_income", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.alter_column("payslips", "taxable_income", server_default=None)


def downgrade() -> None:
    op.drop_column("payslips", "taxable_income")
