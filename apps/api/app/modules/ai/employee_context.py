"""Tra cứu MSNV cho AI chat — đọc CSDL, không bịa số."""

from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.attendance.models import PayPeriod
from app.modules.core.models import User
from app.modules.mdm.models import Department, Employee, Team
from app.modules.payroll.models import Payslip

_MSNV_PREFIX = re.compile(
    r"(?:msnv|mã\s*nhân\s*viên|mã\s*nv|nhân\s*viên|nv|employee)\s*[:\s#\-]*(\d{3,5})",
    re.IGNORECASE,
)
_CODE_BARE = re.compile(r"\b(\d{3,5})\b")


def extract_employee_codes(message: str, *, max_codes: int = 3) -> list[str]:
    """Lấy mã NV từ câu hỏi — ưu tiên sau từ khóa MSNV/NV."""
    text = (message or "").strip()
    if not text:
        return []
    found: list[str] = []
    for m in _MSNV_PREFIX.finditer(text):
        code = m.group(1)
        if code not in found:
            found.append(code)
    if not found:
        for m in _CODE_BARE.finditer(text):
            code = m.group(1)
            # Bỏ qua năm 4 chữ số bắt đầu 19/20 khi không có từ khóa MSNV
            if len(code) == 4 and code.startswith(("19", "20")):
                continue
            if code not in found:
                found.append(code)
    return found[:max_codes]


def _can_lookup_employee(user: User) -> bool:
    return user.role == "admin" or user.has_module("hr") or user.has_module("payroll")


def _fmt_money(v: Decimal | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", ".")


def _employee_block(db: Session, emp: Employee, *, include_payroll: bool) -> str:
    team = db.query(Team).filter(Team.id == emp.team_id).first() if emp.team_id else None
    dept = (
        db.query(Department).filter(Department.id == team.department_id).first()
        if team and team.department_id
        else None
    )
    lines = [
        f"MSNV: {emp.employee_code} | Họ tên: {emp.full_name}",
        f"Trạng thái: {emp.status} | Ngày vào: {emp.join_date or '—'} | Ngày nghỉ: {emp.resign_date or '—'}",
        f"Bộ phận: {dept.name if dept else '—'} ({dept.code if dept else '—'})",
        f"Tổ: {team.name if team else '—'} ({team.code if team else '—'})",
        f"Chức vụ: {emp.position_title or emp.position_code or '—'}",
        f"Lương HĐ: {_fmt_money(emp.contract_salary)} | Kênh lương: {emp.pay_channel}",
        f"BHXH: {'có' if emp.si_enrolled else 'không'} | SĐT: {emp.phone or '—'}",
    ]
    if include_payroll:
        slip = (
            db.query(Payslip, PayPeriod)
            .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
            .filter(Payslip.employee_id == emp.id)
            .order_by(PayPeriod.year.desc(), PayPeriod.month.desc())
            .first()
        )
        if slip:
            ps, pp = slip
            period = f"{pp.year:04d}-{pp.month:02d}"
            lines.append(
                f"Phiếu lương gần nhất ({period}): WD={ps.wd_salary}, PC={ps.allowance_total}, "
                f"OT={ps.ot_pay}, Gross={ps.gross}, Net={ps.net}, trạng thái={ps.status}"
            )
        else:
            lines.append("Phiếu lương: chưa có bản ghi.")
    return "\n".join(lines)


def build_employee_context(db: Session, user: User, message: str) -> tuple[list[str], str]:
    """
    Trả (danh sách mã đã parse, khối ngữ cảnh).
    Chuỗi rỗng nếu không parse được mã hoặc user không có quyền tra cứu.
    """
    codes = extract_employee_codes(message)
    if not codes:
        return [], ""
    if not _can_lookup_employee(user):
        return codes, (
            "### Tra cứu nhân viên\n"
            "Tài khoản không có quyền module Nhân sự/Lương — không đọc được hồ sơ từ CSDL. "
            "Liên hệ Admin cấp quyền `hr` hoặc `payroll`."
        )
    include_payroll = user.role == "admin" or user.has_module("payroll")
    blocks: list[str] = []
    for code in codes:
        emp = db.query(Employee).filter(Employee.employee_code == code).first()
        if emp is None:
            blocks.append(f"MSNV {code}: không tìm thấy trong hệ thống.")
        else:
            blocks.append(_employee_block(db, emp, include_payroll=include_payroll))
    header = "### Dữ liệu nhân viên (đọc từ CSDL — chỉ phân tích, không tự sửa)\n"
    return codes, header + "\n\n".join(blocks)
