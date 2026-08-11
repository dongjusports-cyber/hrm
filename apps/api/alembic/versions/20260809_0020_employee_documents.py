"""employee_documents — hồ sơ giấy scan

Revision ID: 20260809_0020
Revises: 20260809_0019
Create Date: 2026-08-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0020"
down_revision: Union[str, None] = "20260809_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("employee_id", sa.Uuid(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("doc_type", sa.String(length=40), nullable=False, server_default="other"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_employee_documents_employee", "employee_documents", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_documents_employee", table_name="employee_documents")
    op.drop_table("employee_documents")
