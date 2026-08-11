"""Render HTML mẫu in nhân viên — GenusSuite (LabourContract_SW / rptAppliLeter)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from html import escape
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session, joinedload

from app.modules.core.models import User
from app.modules.mdm.models import Employee, Team
from app.modules.mdm.schemas import BulkSalaryRaiseRequest
from app.modules.print.context import build_print_context, load_employee
from app.modules.print.salary_raise import build_raise_appendix_rows

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def require_hr_access(user: User) -> None:
    if user.role == "admin" or user.has_module("hr"):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Trợ Lý AI: bạn không có quyền in mẫu nhân sự.",
    )


def _ctx_dict(db: Session, employee_id: UUID, *, contract_id: UUID | None = None) -> dict:
    emp = load_employee(db, employee_id)
    return asdict(build_print_context(db, emp, contract_id=contract_id))


def render_contract(
    db: Session, employee_id: UUID, *, contract_id: UUID | None = None
) -> str:
    ctx = _ctx_dict(db, employee_id, contract_id=contract_id)
    tpl = _jinja.get_template("labour_contract.html")
    return tpl.render(**ctx)


def render_probation(
    db: Session, employee_id: UUID, *, contract_id: UUID | None = None
) -> str:
    ctx = _ctx_dict(db, employee_id, contract_id=contract_id)
    tpl = _jinja.get_template("probation_agreement.html")
    return tpl.render(**ctx)


def render_salary_raise_appendix(db: Session, body: BulkSalaryRaiseRequest) -> str:
    rows, _effective = build_raise_appendix_rows(db, body)
    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: không có nhân viên nào để in phụ lục tăng lương.",
        )
    tpl = _jinja.get_template("salary_raise_appendix.html")
    return tpl.render(rows=rows)


def _emp_or_404(db: Session, employee_id: UUID) -> Employee:
    emp = (
        db.query(Employee)
        .options(joinedload(Employee.team).joinedload(Team.department))
        .filter(Employee.id == employee_id, Employee.deleted_at.is_(None))
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy nhân viên.")
    return emp


def _wrap(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8"/>
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: "Times New Roman", serif; margin: 24px; color: #111; }}
    h1 {{ text-align: center; font-size: 18px; text-transform: uppercase; }}
    h2 {{ font-size: 15px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    td {{ padding: 4px 8px; vertical-align: top; }}
    .meta {{ margin: 8px 0; }}
    .sign {{ margin-top: 48px; display: flex; justify-content: space-between; }}
    .badge {{ border: 2px solid #333; padding: 16px; width: 320px; margin: 0 auto; text-align: center; }}
    @media print {{ body {{ margin: 12mm; }} }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def render_decision(db: Session, employee_id: UUID, *, decision_no: str | None = None) -> str:
    emp = _emp_or_404(db, employee_id)
    dept = emp.team.department.name if emp.team and emp.team.department else "—"
    team = emp.team.name if emp.team else "—"
    no = decision_no or f"QĐ-{emp.employee_code}-{date.today():%Y%m%d}"
    body = f"""
<h1>Quyết định</h1>
<p class="meta">Số: <strong>{escape(no)}</strong> · Ngày {date.today():%d/%m/%Y}</p>
<h2>V/v bổ nhiệm / điều chuyển / tăng lương</h2>
<p>Căn cứ nhu cầu sản xuất và hồ sơ nhân sự,</p>
<p><strong>Quyết định:</strong></p>
<ul>
  <li>Ông/Bà: <strong>{escape(emp.full_name)}</strong> (MSNV {escape(emp.employee_code)})</li>
  <li>Bộ phận: {escape(dept)}</li>
  <li>Tổ: {escape(team)}</li>
  <li>Chức vụ: {escape(emp.position_title or emp.position_code or "—")}</li>
  <li>Lương HĐ: {emp.contract_salary:,.0f} VND</li>
</ul>
<p><em>Mẫu in tối thiểu — bổ sung nội dung quyết định theo mẫu HR.</em></p>
<div class="sign">
  <div></div>
  <div><strong>GIÁM ĐỐC</strong><br/><br/><br/>……………………</div>
</div>
"""
    return _wrap(f"QĐ {emp.employee_code}", body)
