"""policy_snapshots, payroll_runs, payslips

Revision ID: 20260809_0009
Revises: 20260809_0008
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0009"
down_revision: Union[str, None] = "20260809_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policy_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pay_period_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_snapshots_pay_period_id", "policy_snapshots", ["pay_period_id"])

    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pay_period_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("policy_snapshot_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.ForeignKeyConstraint(["policy_snapshot_id"], ["policy_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payroll_runs_pay_period_id", "payroll_runs", ["pay_period_id"])

    op.create_table(
        "payslips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pay_period_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("policy_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("wd_salary", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("allowance_total", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("ot_pay", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("other_adjustments", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("gross", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("bhxh", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("bhyt", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("bhtn", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("union_fee", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("other_deductions", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("pit_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("net", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("lines", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.ForeignKeyConstraint(["policy_snapshot_id"], ["policy_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pay_period_id", "employee_id", name="uq_payslip_period_emp"),
    )
    op.create_index("ix_payslips_pay_period_id", "payslips", ["pay_period_id"])
    op.create_index("ix_payslips_employee_id", "payslips", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_payslips_employee_id", table_name="payslips")
    op.drop_index("ix_payslips_pay_period_id", table_name="payslips")
    op.drop_table("payslips")
    op.drop_index("ix_payroll_runs_pay_period_id", table_name="payroll_runs")
    op.drop_table("payroll_runs")
    op.drop_index("ix_policy_snapshots_pay_period_id", table_name="policy_snapshots")
    op.drop_table("policy_snapshots")
