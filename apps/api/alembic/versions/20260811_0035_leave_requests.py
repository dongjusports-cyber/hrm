"""Hạng mục 3.6 — leave_requests (21§21.5)

Revision ID: 20260811_0035
Revises: 20260811_0034
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0035"
down_revision: Union[str, None] = "20260811_0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("leave_type_code", sa.String(length=40), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("from_half", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("to_half", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("total_days", sa.Numeric(4, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("document_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_code"], ["leave_types.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leave_requests_status_from_date", "leave_requests", ["status", "from_date"])
    op.create_index("ix_leave_requests_employee_from_date", "leave_requests", ["employee_id", "from_date"])


def downgrade() -> None:
    op.drop_index("ix_leave_requests_employee_from_date", table_name="leave_requests")
    op.drop_index("ix_leave_requests_status_from_date", table_name="leave_requests")
    op.drop_table("leave_requests")
