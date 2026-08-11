"""
Import Excel nhân sự — một bảng map cột (P3b / 06§6.6a).
Cột chuẩn (header hàng 1):
employee_code | full_name | gender | id_number | bank_account | pay_channel |
team_code | department_code | position_title | join_date | resign_date |
contract_signed_at | probation_salary | contract_salary | status | phone

team_code: mã Tổ (khuyến nghị luôn điền — NV thuộc về Tổ, bộ phận suy ra qua Tổ, 21§21.3).
department_code: chỉ cần khi mã Tổ trùng ở nhiều bộ phận (hiếm) để phân giải đúng; nếu để
trống và team_code khớp duy nhất một tổ thì vẫn nạp được. Nếu bỏ trống cả team_code, dòng
vẫn tạo/cập nhật được NV nhưng KHÔNG gán tổ — HR cần vào lưới "Chuyển tổ" bổ sung sau.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.modules.mdm.models import Employee
from app.modules.mdm.schemas import ImportResult
from app.modules.mdm.service import resolve_employee_team

# Map header Excel → field nội bộ (CHỈ một bảng — không nhân đôi)
COLUMN_MAP: dict[str, str] = {
    "employee_code": "employee_code",
    "msnv": "employee_code",
    "mã nv": "employee_code",
    "ma nv": "employee_code",
    "full_name": "full_name",
    "họ tên": "full_name",
    "ho ten": "full_name",
    "gender": "gender",
    "giới tính": "gender",
    "id_number": "id_number",
    "cccd": "id_number",
    "bank_account": "bank_account",
    "stk": "bank_account",
    "pay_channel": "pay_channel",
    "kênh lương": "pay_channel",
    "team_code": "team_code",
    "mã tổ": "team_code",
    "ma to": "team_code",
    "department_code": "department_code",
    "mã bộ phận": "department_code",
    "bo phan": "department_code",
    "position_title": "position_title",
    "chức vụ": "position_title",
    "join_date": "join_date",
    "ngày vào": "join_date",
    "resign_date": "resign_date",
    "ngày nghỉ": "resign_date",
    "ngay nghi": "resign_date",
    "ngày thôi việc": "resign_date",
    "contract_signed_at": "contract_signed_at",
    "ngày ký hđ": "contract_signed_at",
    "probation_salary": "probation_salary",
    "lương thử việc": "probation_salary",
    "contract_salary": "contract_salary",
    "lương hđ": "contract_salary",
    "lương hợp đồng": "contract_salary",
    "status": "status",
    "trạng thái": "status",
    "phone": "phone",
    "sđt": "phone",
}

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _norm_header(val: Any) -> str:
    return str(val or "").strip().lower()


def _parse_date(val: Any) -> date | None:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    text = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"ngày không hợp lệ: {val}")


def _parse_money(val: Any) -> Decimal:
    if val is None or val == "":
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    text = str(val).replace(",", "").replace(" ", "").strip()
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"tiền không hợp lệ: {val}") from exc


def import_employees_xlsx(db: Session, content: bytes, filename: str) -> ImportResult:
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: file Excel tối đa 10MB.",
        )
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: chỉ hỗ trợ file .xlsx.",
        )

    try:
        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: không đọc được file Excel.",
        ) from exc

    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows)
    except StopIteration:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: file Excel trống.") from None

    field_index: dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        key = COLUMN_MAP.get(_norm_header(cell))
        if key and key not in field_index:
            field_index[key] = idx

    if "employee_code" not in field_index or "full_name" not in field_index:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: thiếu cột bắt buộc employee_code (MSNV) và full_name.",
        )

    created = 0
    updated = 0
    errors: list[str] = []

    for row_no, row in enumerate(rows, start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue

        def cell(field: str) -> Any:
            i = field_index.get(field)
            if i is None or i >= len(row):
                return None
            return row[i]

        try:
            code = str(cell("employee_code") or "").strip()
            name = str(cell("full_name") or "").strip()
            if not code or not name:
                raise ValueError("thiếu MSNV hoặc họ tên")

            team_code = cell("team_code")
            dept_code = cell("department_code")
            team = (
                resolve_employee_team(
                    db,
                    None,
                    str(team_code).strip() if team_code else None,
                    str(dept_code).strip() if dept_code else None,
                    required=False,
                )
                if team_code
                else None
            )

            pay = str(cell("pay_channel") or "ATM").strip().upper() or "ATM"
            if pay not in ("ATM", "CASH"):
                pay = "ATM"

            st = str(cell("status") or "active").strip().lower() or "active"
            if st not in ("active", "probation", "resigned", "suspended", "maternity"):
                st = "active"

            values: dict[str, Any] = {
                "full_name": name,
                "gender": (str(cell("gender")).strip() if cell("gender") else None),
                "id_number": (str(cell("id_number")).strip() if cell("id_number") else None),
                "bank_account": (str(cell("bank_account")).strip() if cell("bank_account") else None),
                "pay_channel": pay,
                "position_title": (
                    str(cell("position_title")).strip() if cell("position_title") else None
                ),
                "join_date": _parse_date(cell("join_date")),
                "contract_signed_at": _parse_date(cell("contract_signed_at")),
                "probation_salary": _parse_money(cell("probation_salary")),
                "contract_salary": _parse_money(cell("contract_salary")),
                "status": st,
                "phone": (str(cell("phone")).strip() if cell("phone") else None),
            }
            if "resign_date" in field_index:
                values["resign_date"] = _parse_date(cell("resign_date"))
                if values["resign_date"] and values["status"] == "active":
                    values["status"] = "resigned"
            if team is not None:
                # Chỉ gán/đổi tổ khi dòng có team_code — không xóa tổ đang có của NV cũ
                # khi file import không điền cột này (tránh mất dữ liệu ngoài ý muốn).
                values["team_id"] = team.id

            emp = db.query(Employee).filter(Employee.employee_code == code).first()
            if emp is None:
                emp = Employee(employee_code=code, **values)
                db.add(emp)
                created += 1
            else:
                for k, v in values.items():
                    setattr(emp, k, v)
                emp.deleted_at = None
                updated += 1
        except Exception as exc:  # noqa: BLE001 — gom lỗi từng dòng
            errors.append(f"Dòng {row_no}: {exc}")
            if len(errors) >= 50:
                errors.append("… dừng báo lỗi sau 50 dòng.")
                break

    db.commit()
    detail = (
        f"Trợ Lý AI: import xong — tạo {created}, cập nhật {updated}, "
        f"lỗi {len(errors)} dòng."
    )
    return ImportResult(created=created, updated=updated, errors=errors, detail=detail)
