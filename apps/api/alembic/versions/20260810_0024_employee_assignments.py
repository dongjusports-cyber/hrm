"""V2 hạng mục 1.5 — employee_assignments: lịch sử đổi tổ / chức vụ

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.3.

Không có bảng này thì in lại bảng lương cũ sẽ ra sai tổ. Mỗi lần chuyển tổ (đơn lẻ hay
hàng loạt từ lưới danh sách NV) ghi một dòng ở đây kèm ngày hiệu lực, số quyết định, lý do,
người duyệt — trước khi employees.team_id được cập nhật (23§145).

INDEX (employee_id, effective_from) đúng theo 21§21.6 — tra tổ tại một thời điểm.

Revision ID: 20260810_0024
Revises: 20260810_0023
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0024"
down_revision: Union[str, None] = "20260810_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("position_code", sa.String(length=20), nullable=True),
        sa.Column("job_code", sa.String(length=20), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("decision_no", sa.String(length=50), nullable=True),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["position_code"], ["positions.code"]),
        sa.ForeignKeyConstraint(["job_code"], ["jobs.code"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_assignments_employee_id", "employee_assignments", ["employee_id"])
    op.create_index(
        "ix_employee_assignments_employee_id_effective_from",
        "employee_assignments",
        ["employee_id", "effective_from"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employee_assignments_employee_id_effective_from", table_name="employee_assignments"
    )
    op.drop_index("ix_employee_assignments_employee_id", table_name="employee_assignments")
    op.drop_table("employee_assignments")
