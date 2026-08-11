"""mdm departments + employees

Revision ID: 20260809_0004
Revises: 20260809_0003
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0004"
down_revision: Union[str, None] = "20260809_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("mitapro_names", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_departments_code", "departments", ["code"])

    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_code", sa.String(length=40), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("id_number", sa.String(length=40), nullable=True),
        sa.Column("bank_account", sa.String(length=64), nullable=True),
        sa.Column("pay_channel", sa.String(length=10), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("position_title", sa.String(length=120), nullable=True),
        sa.Column("join_date", sa.Date(), nullable=True),
        sa.Column("contract_signed_at", sa.Date(), nullable=True),
        sa.Column("probation_salary", sa.Numeric(18, 2), nullable=False),
        sa.Column("contract_salary", sa.Numeric(18, 2), nullable=False),
        sa.Column("si_base_override", sa.Numeric(18, 2), nullable=True),
        sa.Column("si_enrolled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("union_fee_override", sa.Numeric(18, 2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resign_date", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code"),
    )
    op.create_index("ix_employees_employee_code", "employees", ["employee_code"])


def downgrade() -> None:
    op.drop_index("ix_employees_employee_code", table_name="employees")
    op.drop_table("employees")
    op.drop_index("ix_departments_code", table_name="departments")
    op.drop_table("departments")
