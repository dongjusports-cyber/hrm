"""Hạng mục 2.5 — 5 bảng chính sách có ngày hiệu lực

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.4 + N3 (mọi bảng chính sách có effective_from/effective_to):
insurance_rates, pit_brackets, pit_deductions, seniority_allowance_tiers, attendance_bonus_rules.

Revision ID: 20260810_0030
Revises: 20260810_0029
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0030"
down_revision: Union[str, None] = "20260810_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "insurance_rates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("si_employee_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("hi_employee_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("ui_employee_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("union_pct", sa.Numeric(18, 2), nullable=False),
        sa.Column("si_base_cap", sa.Numeric(14, 2), nullable=False),
        sa.Column("region_min_wage", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("effective_from"),
    )

    op.create_table(
        "pit_brackets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("from_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("rate_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("effective_from", "seq", name="uq_pit_brackets_from_seq"),
    )
    op.create_index("ix_pit_brackets_effective_from", "pit_brackets", ["effective_from"])

    op.create_table(
        "pit_deductions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("self_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("dependent_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("effective_from"),
    )

    op.create_table(
        "seniority_allowance_tiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("months_from", sa.Integer(), nullable=False),
        sa.Column("months_to", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seniority_allowance_tiers_effective_from", "seniority_allowance_tiers", ["effective_from"])

    op.create_table(
        "attendance_bonus_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("late_count_half", sa.Integer(), nullable=False),
        sa.Column("early_count_half", sa.Integer(), nullable=False),
        sa.Column("late_count_zero", sa.Integer(), nullable=False),
        sa.Column("early_count_zero", sa.Integer(), nullable=False),
        sa.Column("exempt_leave_codes", sa.JSON(), nullable=False),
        sa.Column("full_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("effective_from"),
    )


def downgrade() -> None:
    op.drop_table("attendance_bonus_rules")
    op.drop_index("ix_seniority_allowance_tiers_effective_from", table_name="seniority_allowance_tiers")
    op.drop_table("seniority_allowance_tiers")
    op.drop_table("pit_deductions")
    op.drop_index("ix_pit_brackets_effective_from", table_name="pit_brackets")
    op.drop_table("pit_brackets")
    op.drop_table("insurance_rates")
