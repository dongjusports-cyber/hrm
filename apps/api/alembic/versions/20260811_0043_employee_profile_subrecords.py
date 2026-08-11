"""5.1 — employee_educations, employee_experiences, employee_health_checks."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0043"
down_revision = "20260811_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_educations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("school_name", sa.String(200), nullable=False),
        sa.Column("major", sa.String(120), nullable=True),
        sa.Column("degree_code", sa.String(40), nullable=True),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_educations_employee_id", "employee_educations", ["employee_id"])

    op.create_table(
        "employee_experiences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("position_title", sa.String(120), nullable=True),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_experiences_employee_id", "employee_experiences", ["employee_id"])

    op.create_table(
        "employee_health_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("facility_name", sa.String(200), nullable=True),
        sa.Column("result_summary", sa.String(200), nullable=True),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_health_checks_employee_id", "employee_health_checks", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_health_checks_employee_id", table_name="employee_health_checks")
    op.drop_table("employee_health_checks")
    op.drop_index("ix_employee_experiences_employee_id", table_name="employee_experiences")
    op.drop_table("employee_experiences")
    op.drop_index("ix_employee_educations_employee_id", table_name="employee_educations")
    op.drop_table("employee_educations")
