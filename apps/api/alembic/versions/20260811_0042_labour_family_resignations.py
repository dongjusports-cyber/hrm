"""5.2–5.4 — labour_contracts, employee_family_members, employee_resignations (21§21.3)."""

from alembic import op
import sqlalchemy as sa

revision = "20260811_0042"
down_revision = "20260811_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labour_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("contract_type_code", sa.String(20), nullable=False),
        sa.Column("seq_no", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("sign_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("base_salary", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("position_code", sa.String(20), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["position_code"], ["positions.code"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_labour_contracts_employee_id_start_date",
        "labour_contracts",
        ["employee_id", "start_date"],
    )
    op.create_index(
        "ix_labour_contracts_end_date_active",
        "labour_contracts",
        ["end_date"],
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "employee_family_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_code", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("id_number", sa.String(40), nullable=True),
        sa.Column("is_tax_dependent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dependent_from", sa.Date(), nullable=True),
        sa.Column("dependent_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_family_members_employee_id", "employee_family_members", ["employee_id"])

    op.create_table(
        "employee_resignations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("seq_no", sa.SmallInteger(), nullable=False),
        sa.Column("resign_type_code", sa.String(20), nullable=False),
        sa.Column("applied_date", sa.Date(), nullable=True),
        sa.Column("last_working_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("severance_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severance_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("handover_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rehired_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "seq_no", name="uq_employee_resignations_emp_seq"),
    )
    op.create_index("ix_employee_resignations_employee_id", "employee_resignations", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_resignations_employee_id", table_name="employee_resignations")
    op.drop_table("employee_resignations")
    op.drop_index("ix_employee_family_members_employee_id", table_name="employee_family_members")
    op.drop_table("employee_family_members")
    op.drop_index("ix_labour_contracts_end_date_active", table_name="labour_contracts")
    op.drop_index("ix_labour_contracts_employee_id_start_date", table_name="labour_contracts")
    op.drop_table("labour_contracts")
