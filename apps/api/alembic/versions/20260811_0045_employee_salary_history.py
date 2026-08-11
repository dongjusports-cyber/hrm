"""21§21.3 — employee_salary_history: lịch sử lương từng NV."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0045"
down_revision = "20260811_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_salary_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("field_code", sa.String(length=30), nullable=False, server_default="contract_salary"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("old_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("new_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("decision_no", sa.String(length=50), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employee_salary_history_employee_id",
        "employee_salary_history",
        ["employee_id"],
    )
    op.create_index(
        "ix_employee_salary_history_employee_id_effective_from",
        "employee_salary_history",
        ["employee_id", "effective_from"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employee_salary_history_employee_id_effective_from",
        table_name="employee_salary_history",
    )
    op.drop_index("ix_employee_salary_history_employee_id", table_name="employee_salary_history")
    op.drop_table("employee_salary_history")
