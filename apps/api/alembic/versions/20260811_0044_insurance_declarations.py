"""5.5 — insurance_declarations (21§21.3)."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0044"
down_revision = "20260811_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insurance_declarations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("declaration_type", sa.String(length=20), nullable=False),
        sa.Column("effective_month", sa.String(length=7), nullable=False),
        sa.Column("old_salary", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("new_salary", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("batch_no", sa.String(length=30), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_insurance_declarations_effective_month_status",
        "insurance_declarations",
        ["effective_month", "status"],
    )
    op.create_index(
        "ix_insurance_declarations_employee_id",
        "insurance_declarations",
        ["employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_insurance_declarations_employee_id", table_name="insurance_declarations")
    op.drop_index("ix_insurance_declarations_effective_month_status", table_name="insurance_declarations")
    op.drop_table("insurance_declarations")
