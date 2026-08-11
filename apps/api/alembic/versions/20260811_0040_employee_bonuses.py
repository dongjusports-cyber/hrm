"""4.8 — employee_bonuses (THR_BONUS, 21§21.6)."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0040"
down_revision = "20260811_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_bonuses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("bonus_year", sa.Integer(), nullable=False),
        sa.Column("seq_times", sa.SmallInteger(), nullable=False),
        sa.Column("bonus_code", sa.String(40), nullable=False, server_default="TET"),
        sa.Column("base_salary", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("bonus_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("bonus_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("pay_period_id", sa.Uuid(), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "bonus_year", "seq_times", name="uq_employee_bonus_year_seq"),
    )
    op.create_index("ix_employee_bonuses_employee_id", "employee_bonuses", ["employee_id"])
    op.create_index("ix_employee_bonuses_pay_period_id", "employee_bonuses", ["pay_period_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_bonuses_pay_period_id", table_name="employee_bonuses")
    op.drop_index("ix_employee_bonuses_employee_id", table_name="employee_bonuses")
    op.drop_table("employee_bonuses")
