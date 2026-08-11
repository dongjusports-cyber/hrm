"""leave_types, pay_periods, timesheet_months, adjustments

Revision ID: 20260809_0007
Revises: 20260809_0006
Create Date: 2026-08-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0007"
down_revision: Union[str, None] = "20260809_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_types",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("paid_by_company", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("counts_as_unauthorized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "pay_periods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("official_work_days", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("salary_divisor", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "month", name="uq_pay_period_ym"),
    )
    op.create_table(
        "timesheet_months",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pay_period_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("worked_days", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("al_days", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("rem_days", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("late_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ot_hours_weekday", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("ot_hours_weekend", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("ot_hours_holiday", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pay_period_id", "employee_id", name="uq_timesheet_period_emp"),
    )
    op.create_index("ix_timesheet_months_pay_period_id", "timesheet_months", ["pay_period_id"])
    op.create_index("ix_timesheet_months_employee_id", "timesheet_months", ["employee_id"])
    op.create_table(
        "timesheet_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pay_period_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("leave_code", sa.String(length=40), nullable=True),
        sa.Column("days", sa.Numeric(8, 4), nullable=True),
        sa.Column("ot_type", sa.String(length=40), nullable=True),
        sa.Column("ot_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["leave_code"], ["leave_types.code"]),
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_timesheet_adjustments_pay_period_id", "timesheet_adjustments", ["pay_period_id"])
    op.create_index("ix_timesheet_adjustments_employee_id", "timesheet_adjustments", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_timesheet_adjustments_employee_id", table_name="timesheet_adjustments")
    op.drop_index("ix_timesheet_adjustments_pay_period_id", table_name="timesheet_adjustments")
    op.drop_table("timesheet_adjustments")
    op.drop_index("ix_timesheet_months_employee_id", table_name="timesheet_months")
    op.drop_index("ix_timesheet_months_pay_period_id", table_name="timesheet_months")
    op.drop_table("timesheet_months")
    op.drop_table("pay_periods")
    op.drop_table("leave_types")
