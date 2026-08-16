"""Xuất Excel danh sách NV (hạng mục 1.4) — chỉ xuất đúng cột đang hiện, đúng bộ lọc đang bật
(HIEN_PHAP 23§ "Xuất Excel"). Không có cột riêng cho việc này — dùng lại `EmployeeOut` từ
`service.list_employees` để lưới và file Excel luôn khớp số với nhau (một nguồn dữ liệu).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from app.modules.core.export_log import log_export
from app.modules.core.models import User
from app.modules.mdm import service
from app.modules.mdm.schemas import EmployeeOut

# Toàn bộ cột có thể xuất — khoá phải khớp field của EmployeeOut hoặc tên suy ra bên dưới.
# Thứ tự ở đây cũng là thứ tự cột trong file Excel.
EXPORT_COLUMNS: dict[str, str] = {
    "employee_code": "MSNV",
    "full_name": "Họ tên",
    "contract_salary": "Lương HĐ",
    "department_code": "Bộ phận",
    "team_code": "Tổ",
    "position_title": "Chức vụ",
    "join_date": "Ngày vào",
    "contract_signed_at": "Ngày Ký HĐ",
    "seniority_label": "Thâm niên",
    "contract_type_label": "Loại HĐ",
    "total_salary": "Lương Tổng",
    "status": "Trạng thái",
    "account_status_label": "Tài khoản",
}

STATUS_LABEL = {
    "active": "Chính thức",
    "probation": "Thử việc",
    "resigned": "Thôi việc",
    "suspended": "Tạm ngưng",
    "maternity": "Thai sản",
}


def _cell_value(emp: EmployeeOut, key: str):
    val = getattr(emp, key, None)
    if key == "status":
        return STATUS_LABEL.get(val, val)
    if isinstance(val, (date, datetime)):
        return val.strftime("%d/%m/%Y")
    if isinstance(val, Decimal):
        return int(val)
    if val is None:
        return ""
    return val


def resolve_export_columns(columns: str | None) -> list[str]:
    """`columns` là chuỗi CSV các khoá trong EXPORT_COLUMNS; rỗng/không hợp lệ → xuất hết."""
    if not columns:
        return list(EXPORT_COLUMNS.keys())
    picked = [c.strip() for c in columns.split(",") if c.strip() in EXPORT_COLUMNS]
    return picked or list(EXPORT_COLUMNS.keys())


def build_employees_export_xlsx(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    department_id: UUID | None,
    team_id: UUID | None,
    columns: list[str],
) -> tuple[bytes, int, str]:
    rows = service.list_employees(
        db, q=q, status=status, department_id=department_id, team_id=team_id
    )

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Danh_sach_NV"

    bold = Font(bold=True)
    ws.append([EXPORT_COLUMNS[c] for c in columns])
    for cell in ws[1]:
        cell.font = bold

    for emp in rows:
        ws.append([_cell_value(emp, c) for c in columns])

    ws.freeze_panes = "A2"

    filename = f"danh_sach_nv_{date.today().isoformat()}.xlsx"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue(), len(rows), filename


def export_employees_channel(
    db: Session,
    user: User,
    *,
    q: str | None,
    status: str | None,
    department_id: UUID | None,
    team_id: UUID | None,
    columns: str | None,
) -> tuple[bytes, str]:
    cols = resolve_export_columns(columns)
    data, row_count, filename = build_employees_export_xlsx(
        db, q=q, status=status, department_id=department_id, team_id=team_id, columns=cols
    )
    log_export(
        db,
        user_id=user.id,
        kind="employees",
        period=None,
        row_count=row_count,
        filename=filename,
    )
    return data, filename
