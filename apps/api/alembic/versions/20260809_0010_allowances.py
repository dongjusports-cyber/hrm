"""allowance_types + employee assignments

Revision ID: 20260809_0010
Revises: 20260809_0009
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0010"
down_revision: Union[str, None] = "20260809_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "allowance_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("proration", sa.String(length=40), nullable=False),
        sa.Column("include_in_si_base", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("include_in_ot_base", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("default_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_allowance_types_code", "allowance_types", ["code"])

    op.create_table(
        "employee_allowance_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("allowance_type_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["allowance_type_id"], ["allowance_types.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "allowance_type_id", name="uq_emp_allowance"),
    )
    op.create_index("ix_employee_allowance_assignments_employee_id", "employee_allowance_assignments", ["employee_id"])
    op.create_index(
        "ix_employee_allowance_assignments_allowance_type_id",
        "employee_allowance_assignments",
        ["allowance_type_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employee_allowance_assignments_allowance_type_id",
        table_name="employee_allowance_assignments",
    )
    op.drop_index("ix_employee_allowance_assignments_employee_id", table_name="employee_allowance_assignments")
    op.drop_table("employee_allowance_assignments")
    op.drop_index("ix_allowance_types_code", table_name="allowance_types")
    op.drop_table("allowance_types")
