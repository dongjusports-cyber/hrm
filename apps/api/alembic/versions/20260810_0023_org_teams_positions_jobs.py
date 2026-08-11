"""V2 hạng mục 1.1 — tổ chức: teams, positions, jobs; mở rộng departments; employees.team_id/position_code/job_code

Theo HIEN_PHAP/21_SCHEMA_V2.md §21.2 + §21.3.

- departments: + name_local, dept_type, sort_order, effective_from, effective_to.
  is_active (cột lưu) bị BỎ — chuyển thành thuộc tính suy ra từ effective_to trong model
  (Department.is_active là hybrid_property, không phải cột DB).
- teams (MỚI): cấp Tổ, cha là departments. default_shift_id CHƯA thêm (chờ work_shifts ở
  hạng mục 2.4).
  LỆCH so với 21§21.2: bỏ `UNIQUE(department_id, code)`. Dữ liệu thật THR_ABWORKGRP cho thấy
  mã tổ được tái dùng theo thời gian — ví dụ mã '19' ở Production: tổ "Staff" đóng
  2007-07-17, cùng ngày mã '19' mở lại cho tổ "Pro Admin" (PK 214 và 287). Ràng buộc unique
  cứng sẽ chặn đúng dữ liệu gốc. Thay bằng index thường (department_id, code) để tra nhanh;
  không kiểm tra chồng lấp effective_from/to ở tầng DB (N — vừa đủ, không exclusion
  constraint cho quy mô 500 người).
- positions (MỚI), jobs (MỚI): danh mục PK là mã (varchar), không dùng UUID.
- employees: + team_id (FK teams, NULL — sẽ ép NOT NULL sau khi có dữ liệu ở 1.2/1.3),
  + position_code (FK positions.code), + job_code (FK jobs.code).
  department_id GIỮ LẠI, chưa xóa (N1 — mở rộng, không đập).

Revision ID: 20260810_0023
Revises: 20260810_0022
Create Date: 2026-08-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0023"
down_revision: Union[str, None] = "20260810_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Dữ liệu departments hiện có là dữ liệu test (HIEN_PHAP 20§N2) — dùng ngày sentinel
# cho effective_from của các bản ghi cũ, không ảnh hưởng nghiệp vụ đã chốt.
_SENTINEL_EFFECTIVE_FROM = "2020-01-01"


def upgrade() -> None:
    # ---- departments: mở rộng ----
    op.add_column("departments", sa.Column("name_local", sa.String(length=200), nullable=True))
    op.add_column("departments", sa.Column("dept_type", sa.String(length=20), nullable=True))
    op.add_column(
        "departments",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "departments",
        sa.Column(
            "effective_from",
            sa.Date(),
            nullable=False,
            server_default=sa.text(f"'{_SENTINEL_EFFECTIVE_FROM}'"),
        ),
    )
    op.add_column("departments", sa.Column("effective_to", sa.Date(), nullable=True))
    op.drop_column("departments", "is_active")

    # ---- positions (MỚI) ----
    op.create_table(
        "positions",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_local", sa.String(length=200), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_management", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("code"),
    )

    # ---- jobs (MỚI) ----
    op.create_table(
        "jobs",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_local", sa.String(length=200), nullable=True),
        sa.Column("is_hazardous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("code"),
    )

    # ---- teams (MỚI) ----
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_local", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "effective_from",
            sa.Date(),
            nullable=False,
            server_default=sa.text(f"'{_SENTINEL_EFFECTIVE_FROM}'"),
        ),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_department_id", "teams", ["department_id"])
    op.create_index("ix_teams_department_id_code", "teams", ["department_id", "code"])

    # ---- employees: + team_id, position_code, job_code ----
    op.add_column("employees", sa.Column("team_id", sa.Uuid(), nullable=True))
    op.add_column("employees", sa.Column("position_code", sa.String(length=20), nullable=True))
    op.add_column("employees", sa.Column("job_code", sa.String(length=20), nullable=True))
    op.create_foreign_key("fk_employees_team_id", "employees", "teams", ["team_id"], ["id"])
    op.create_foreign_key(
        "fk_employees_position_code", "employees", "positions", ["position_code"], ["code"]
    )
    op.create_foreign_key("fk_employees_job_code", "employees", "jobs", ["job_code"], ["code"])
    op.create_index("ix_employees_team_id", "employees", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_teams_department_id_code", table_name="teams")
    op.drop_index("ix_employees_team_id", table_name="employees")
    op.drop_constraint("fk_employees_job_code", "employees", type_="foreignkey")
    op.drop_constraint("fk_employees_position_code", "employees", type_="foreignkey")
    op.drop_constraint("fk_employees_team_id", "employees", type_="foreignkey")
    op.drop_column("employees", "job_code")
    op.drop_column("employees", "position_code")
    op.drop_column("employees", "team_id")

    op.drop_index("ix_teams_department_id", table_name="teams")
    op.drop_table("teams")
    op.drop_table("jobs")
    op.drop_table("positions")

    op.add_column(
        "departments",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_column("departments", "effective_to")
    op.drop_column("departments", "effective_from")
    op.drop_column("departments", "sort_order")
    op.drop_column("departments", "dept_type")
    op.drop_column("departments", "name_local")
