"""Dọn dẹp ĐỢT 1 — bỏ employees.department_id (21§21.3, nghiệm thu 24§ĐỢT 1 mục 5)

Bộ phận suy ra qua `teams.department_id`, không lưu hai chỗ. Cột này bị giữ lại ở hạng
mục 1.1 (N1 — mở rộng, không đập) để không phá code đang đọc nó giữa lúc chuyển đổi.
Nay hạng mục 1.4/1.5 đã xong, mọi code đọc/ghi department_id của NV đã chuyển sang đọc
qua `Employee.team.department_id` (hybrid_property, xem app/modules/mdm/models.py) —
đủ điều kiện xóa cột thật.

Trước khi xóa, xác minh không có NV nào có department_id lệch với department_id suy ra
từ team_id hiện tại (an toàn dữ liệu — nếu có dòng lệch, dừng và báo, không tự xóa).

Revision ID: 20260810_0025
Revises: 20260810_0024
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0025"
down_revision: Union[str, None] = "20260810_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    mismatched = conn.execute(
        sa.text(
            """
            SELECT e.employee_code, e.department_id AS old_dept, t.department_id AS team_dept
            FROM employees e
            LEFT JOIN teams t ON t.id = e.team_id
            WHERE e.department_id IS NOT NULL
              AND (t.department_id IS NULL OR e.department_id <> t.department_id)
            """
        )
    ).fetchall()
    if mismatched:
        codes = ", ".join(r[0] for r in mismatched[:20])
        raise RuntimeError(
            "Trợ Lý AI: dừng migration — có NV mà department_id cũ KHÁC department suy ra "
            f"từ team hiện tại (kiểm tra lại trước khi xóa cột): {codes}"
        )

    op.drop_constraint("employees_department_id_fkey", "employees", type_="foreignkey")
    op.drop_column("employees", "department_id")


def downgrade() -> None:
    op.add_column("employees", sa.Column("department_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "employees_department_id_fkey", "employees", "departments", ["department_id"], ["id"]
    )
    # Khôi phục giá trị suy ra từ team — không giữ được giá trị gốc trước upgrade (đã suy ra 1-1).
    op.execute(
        sa.text(
            """
            UPDATE employees e
            SET department_id = t.department_id
            FROM teams t
            WHERE t.id = e.team_id
            """
        )
    )
