"""Bước D — bảng employee_wt_regimes (chế độ về sớm Thai sản / Nuôi con, 22§22.14).

Chuỗi revision: 0049 -> A 0050 -> D 0051.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260815_0051"
down_revision = "20260815_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_wt_regimes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("regime_type", sa.String(length=20), nullable=False),
        sa.Column("hours_early", sa.SmallInteger(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("hours_early IN (1, 2, 3)", name="ck_wt_regime_hours_early"),
        sa.CheckConstraint("date_to >= date_from", name="ck_wt_regime_dates"),
    )
    op.create_index(
        "ix_wt_regimes_employee_dates",
        "employee_wt_regimes",
        ["employee_id", "date_from", "date_to"],
    )


def downgrade() -> None:
    op.drop_index("ix_wt_regimes_employee_dates", table_name="employee_wt_regimes")
    op.drop_table("employee_wt_regimes")
