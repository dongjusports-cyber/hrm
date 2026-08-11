"""4.7 — annual_leave_ledger + annual_leave_entries (22§22.7)."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0039"
down_revision = "20260811_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "annual_leave_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("opening_balance", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("accrued", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("used", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("adjusted", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("closing_balance", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("last_accrued_month", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "year", name="uq_annual_leave_ledger_emp_year"),
    )
    op.create_index("ix_annual_leave_ledger_employee_id", "annual_leave_ledger", ["employee_id"])

    op.create_table(
        "annual_leave_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ledger_id", sa.Uuid(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("days", sa.Numeric(4, 2), nullable=False),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ledger_id"], ["annual_leave_ledger.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_annual_leave_entries_ledger_id", "annual_leave_entries", ["ledger_id"])
    op.create_index("ix_annual_leave_entries_reference", "annual_leave_entries", ["reference"])


def downgrade() -> None:
    op.drop_index("ix_annual_leave_entries_reference", table_name="annual_leave_entries")
    op.drop_index("ix_annual_leave_entries_ledger_id", table_name="annual_leave_entries")
    op.drop_table("annual_leave_entries")
    op.drop_index("ix_annual_leave_ledger_employee_id", table_name="annual_leave_ledger")
    op.drop_table("annual_leave_ledger")
