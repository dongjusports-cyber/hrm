"""Phụ lục tăng lương — map DJ HRM → mẫu PHU LUC TANG LUONG (GenusSuite)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.modules.mdm import labour_contract_flow as lcf
from app.modules.mdm.models import Employee, Job, Position, Team
from app.modules.mdm.schemas import BulkSalaryRaiseRequest
from app.modules.mdm.service import _raise_target_query, _resolve_raise_target
from app.modules.payroll.money import D
from app.modules.print.context import COMPANY, EMPLOYER, _allowance_map, _pick_contract, fmt_date, fmt_vnd


def _contract_no(db: Session, emp: Employee) -> str:
    contract = _pick_contract(db, emp, None)
    if contract and contract.contract_type_code:
        return lcf.format_contract_no(emp.employee_code, contract.contract_type_code)
    return "—"


def _position_allowance(db: Session, emp_id: UUID) -> Decimal:
    allow = _allowance_map(db, emp_id)
    return allow.get("POSITION", Decimal("0"))


def build_raise_appendix_rows(
    db: Session, body: BulkSalaryRaiseRequest
) -> tuple[list[dict], date]:
    q, _dept = _raise_target_query(db, body)
    _target, _target_label, at = _resolve_raise_target(db, body)
    effective = body.effective_from or date.today()
    sign = effective

    rows: list[dict] = []
    for emp in q.options(joinedload(Employee.team).joinedload(Team.department)).all():
        pos: Position | None = db.get(Position, emp.position_code) if emp.position_code else None
        job: Job | None = db.get(Job, emp.job_code) if emp.job_code else None
        position_vn = (pos.name_local or pos.name if pos else None) or emp.position_title or "—"
        position_en = (pos.name if pos else None) or emp.position_title or "—"
        job_vn = (job.name_local or job.name if job else None) or "—"
        job_en = (job.name if job else None) or "—"

        pos_amt = _position_allowance(db, emp.id)
        if body.target == "contract_salary":
            basic_old = D(emp.contract_salary)
            basic_new = basic_old + body.amount
            basic_delta = body.amount
            pos_old = pos_amt
            pos_new = pos_amt
            pos_delta = Decimal("0")
        elif body.target == "probation_salary":
            basic_old = D(emp.probation_salary)
            basic_new = basic_old + body.amount
            basic_delta = body.amount
            pos_old = pos_amt
            pos_new = pos_amt
            pos_delta = Decimal("0")
        else:
            assert at is not None
            basic_old = D(emp.contract_salary)
            basic_new = basic_old
            basic_delta = Decimal("0")
            if at.code == "POSITION":
                pos_old = pos_amt
                pos_new = pos_amt + body.amount
                pos_delta = body.amount
            else:
                pos_old = pos_amt
                pos_new = pos_amt
                pos_delta = Decimal("0")

        rows.append(
            {
                "company": COMPANY,
                "employer": EMPLOYER,
                "employee_code": emp.employee_code,
                "full_name": emp.full_name,
                "birth_date": fmt_date(emp.birth_date),
                "birth_place": emp.birth_place_code or COMPANY["sign_place"],
                "id_number": emp.id_number or "—",
                "address": emp.permanent_address or emp.temporary_address or "—",
                "position_vn": position_vn,
                "position_en": position_en,
                "job_vn": job_vn,
                "job_en": job_en,
                "contract_no": _contract_no(db, emp),
                "basic_old": fmt_vnd(basic_old),
                "basic_new": fmt_vnd(basic_new),
                "basic_delta": fmt_vnd(basic_delta),
                "pos_old": fmt_vnd(pos_old),
                "pos_new": fmt_vnd(pos_new),
                "pos_delta": fmt_vnd(pos_delta),
                "effective_date": fmt_date(effective),
                "sign_day": f"{sign.day:02d}",
                "sign_month": f"{sign.month:02d}",
                "sign_year": str(sign.year),
            }
        )
    return rows, effective
