"""employee_violations — lịch sử vi phạm / biên bản

Revision ID: 20260809_0019
Revises: 20260809_0018
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0019"
down_revision: Union[str, None] = "20260809_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_violations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("employee_id", sa.Uuid(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("penalty", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("attachment_path", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_employee_violations_employee", "employee_violations", ["employee_id"])
    op.create_index("ix_employee_violations_occurred", "employee_violations", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_employee_violations_occurred", table_name="employee_violations")
    op.drop_index("ix_employee_violations_employee", table_name="employee_violations")
    op.drop_table("employee_violations")
