"""Dữ liệu mẫu in — map DJ HRM → trường GenusSuite (LabourContract_SW / rptAppliLeter)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.modules.mdm import labour_contract_flow as lcf
from app.modules.mdm.models import Employee, Job, LabourContract, Position, Team
from app.modules.payroll.engine_allowances import seniority_monthly
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent
from app.modules.payroll.money import D
from app.modules.payroll.seed_allowances import SENIORITY_RULES


# Thông tin công ty / người đại diện — theo mẫu GenusSuite (cố định DJ).
COMPANY = {
    "name_en": "DONGJU SPORTS VIET NAM CO., LTD",
    "name_vi": "CÔNG TY TNHH DONGJU SPORTS VIỆT NAM",
    "address_en": (
        "Lot 33-7, 33-8, Road D11, Phuoc Dong industrial park, "
        "Phuoc Dong village, Go Dau Dist, Tay Ninh Province"
    ),
    "address_vi": "Lô 33-7,33-8, Đường D11, KCN Phước Đông, Gia Lộc, Tây Ninh",
    "work_site_vi": "Lô 33-7,33-8, Đường D11, KCN Phước Đông, Gia Lộc, TN",
    "work_site_en": (
        "Lot 33-7, 33-8, Road D11, Phuoc Dong industrial park, "
        "Gia Loc village, Tay Ninh Province"
    ),
    "phone": "0276 3535976",
    "sign_place": "Tây Ninh",
}

EMPLOYER = {
    "name": "KIM JEONGTAG",
    "title_vi": "Tổng quản lý, đại diện cho Công ty TNHH DONGJU SPORTS VIỆT NAM",
    "title_en": "General Manager, on behalf of Dongju Sports Viet Nam Co., Ltd.",
    "passport": "M080H0341",
    "passport_date": "17/02/2022",
    "address": "#214, 3-2-3 Chome, Sumiregaoka, Takasazuka-shi, Hyogo, Japan",
}


def fmt_date(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def fmt_vnd(amount: Decimal | int | float | None) -> str:
    if amount is None:
        return "0"
    return f"{int(D(amount)):,}".replace(",", ".")


def _month_add(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def probation_end_date(join_date: date | None, contract_end: date | None) -> date | None:
    if contract_end:
        return contract_end
    if not join_date:
        return None
    # GenusSuite: ADD_MONTHS(JOIN_DATE - 1 day, 1 month)
    return _month_add(join_date - timedelta(days=1), 1)


def _gender_vn(gender: str | None) -> str:
    if not gender:
        return "—"
    g = gender.strip().lower()
    if g in ("f", "female", "nu", "nữ", "0"):
        return "Nữ"
    if g in ("m", "male", "nam", "1"):
        return "Nam"
    return gender


def _allowance_map(db: Session, emp_id: UUID) -> dict[str, Decimal]:
    rows = (
        db.query(EmployeeAllowanceAssignment, PayComponent)
        .join(PayComponent, PayComponent.id == EmployeeAllowanceAssignment.allowance_type_id)
        .filter(EmployeeAllowanceAssignment.employee_id == emp_id, PayComponent.is_active.is_(True))
        .all()
    )
    out: dict[str, Decimal] = {}
    for asg, pc in rows:
        out[pc.code] = D(asg.amount) if asg.amount is not None else D(pc.default_amount)
    return out


def _pick_contract(
    db: Session, emp: Employee, contract_id: UUID | None
) -> LabourContract | None:
    if contract_id:
        return (
            db.query(LabourContract)
            .filter(LabourContract.id == contract_id, LabourContract.employee_id == emp.id)
            .one_or_none()
        )
    active = (
        db.query(LabourContract)
        .filter(LabourContract.employee_id == emp.id, LabourContract.status == "active")
        .order_by(LabourContract.start_date.desc())
        .first()
    )
    if active:
        return active
    return (
        db.query(LabourContract)
        .filter(LabourContract.employee_id == emp.id)
        .order_by(LabourContract.start_date.desc())
        .first()
    )


@dataclass(frozen=True)
class PrintContext:
    """Ngữ cảnh render Jinja2 — một NV + HĐ (nếu có)."""

    company: dict
    employer: dict
    employee_code: str
    full_name: str
    birth_date: str
    id_number: str
    address: str
    gender_vn: str
    join_date: str
    position_vn: str
    position_en: str
    job_vn: str
    job_en: str
    contract_no: str
    contract_type: str
    is_indefinite: bool
    contract_kind_vn: str
    contract_kind_en: str
    start_date: str
    end_date: str
    sign_day: str
    sign_month: str
    sign_year: str
    basic_salary: str
    probation_salary: str
    position_allow: str
    tech_allow: str
    attend_allow: str
    transport_allow: str
    training_allow: str
    treat_allow: str
    seniority_allow: str
    total_official_salary: str
    probation_total: str
    probation_end: str
    pay_channel_vn: str
    pay_channel_en: str
    print_date: str


def build_print_context(
    db: Session,
    emp: Employee,
    *,
    contract_id: UUID | None = None,
) -> PrintContext:
    contract = _pick_contract(db, emp, contract_id)
    allow = _allowance_map(db, emp.id)

    pos: Position | None = None
    if emp.position_code:
        pos = db.get(Position, emp.position_code)
    job: Job | None = None
    if emp.job_code:
        job = db.get(Job, emp.job_code)

    position_vn = (pos.name_local or pos.name if pos else None) or emp.position_title or "—"
    position_en = (pos.name if pos else None) or emp.position_title or "—"
    job_vn = (job.name_local or job.name if job else None) or "—"
    job_en = (job.name if job else None) or "—"

    ctype = (contract.contract_type_code if contract else "").upper()
    is_tv = ctype == "TV" or emp.status == "probation"
    is_indefinite = ctype == "VTH" or (contract and contract.end_date is None and not is_tv)

    if is_tv:
        kind_vn, kind_en = "Thử việc", "Probation"
    elif is_indefinite:
        kind_vn, kind_en = "Không xác định thời hạn", "Indefinite Labour Contract"
    else:
        kind_vn, kind_en = "Xác định thời hạn — 01 năm", "Definite — 01 year"

    start = contract.start_date if contract else emp.join_date
    end = contract.end_date if contract else None
    sign = contract.sign_date if contract and contract.sign_date else start or date.today()

    basic = D(contract.base_salary if contract else emp.contract_salary)
    prob = D(emp.probation_salary)

    pos_amt = allow.get("POSITION", Decimal("0"))
    tech_amt = allow.get("TECH", Decimal("0"))
    attend_amt = allow.get("ATTEND", Decimal("0"))
    trans_amt = allow.get("TRANSPORT", Decimal("0"))
    train_amt = allow.get("TRAINING", Decimal("0"))
    treat_amt = allow.get("TOXIC", Decimal("0"))
    senior_amt = allow.get("SENIORITY", Decimal("0"))
    if senior_amt == 0 and emp.join_date:
        senior_amt = seniority_monthly(emp.join_date, date.today(), SENIORITY_RULES)

    total_official = basic + pos_amt + tech_amt + attend_amt + trans_amt + train_amt + treat_amt + senior_amt
    prob_total = prob + pos_amt + tech_amt + attend_amt + trans_amt + train_amt + treat_amt

    contract_no = "—"
    if contract and contract.contract_type_code:
        contract_no = lcf.format_contract_no(emp.employee_code, contract.contract_type_code)
    elif start:
        contract_no = f"{emp.employee_code}/HĐ1"

    channel = (emp.pay_channel or "ATM").upper()
    if channel == "ATM":
        pay_vn, pay_en = "chuyển khoản", "transfer"
    else:
        pay_vn, pay_en = "tiền mặt", "cash"

    prob_end = probation_end_date(emp.join_date, end if is_tv else None)

    return PrintContext(
        company=COMPANY,
        employer=EMPLOYER,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        birth_date=fmt_date(emp.birth_date),
        id_number=emp.id_number or "—",
        address=emp.permanent_address or emp.temporary_address or "—",
        gender_vn=_gender_vn(emp.gender),
        join_date=fmt_date(emp.join_date),
        position_vn=position_vn,
        position_en=position_en,
        job_vn=job_vn,
        job_en=job_en,
        contract_no=contract_no,
        contract_type=ctype or "—",
        is_indefinite=is_indefinite,
        contract_kind_vn=kind_vn,
        contract_kind_en=kind_en,
        start_date=fmt_date(start),
        end_date=fmt_date(end) if end else "Không xác định",
        sign_day=f"{sign.day:02d}",
        sign_month=f"{sign.month:02d}",
        sign_year=str(sign.year),
        basic_salary=fmt_vnd(basic),
        probation_salary=fmt_vnd(prob),
        position_allow=fmt_vnd(pos_amt),
        tech_allow=fmt_vnd(tech_amt),
        attend_allow=fmt_vnd(attend_amt),
        transport_allow=fmt_vnd(trans_amt),
        training_allow=fmt_vnd(train_amt),
        treat_allow=fmt_vnd(treat_amt),
        seniority_allow=fmt_vnd(senior_amt),
        total_official_salary=fmt_vnd(total_official),
        probation_total=fmt_vnd(prob_total),
        probation_end=fmt_date(prob_end),
        pay_channel_vn=pay_vn,
        pay_channel_en=pay_en,
        print_date=fmt_date(date.today()),
    )


def load_employee(db: Session, employee_id: UUID) -> Employee:
    from fastapi import HTTPException

    emp = (
        db.query(Employee)
        .options(joinedload(Employee.team).joinedload(Team.department))
        .filter(Employee.id == employee_id, Employee.deleted_at.is_(None))
        .one_or_none()
    )
    if emp is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy nhân viên.")
    return emp
