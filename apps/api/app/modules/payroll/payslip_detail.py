"""HR phiếu lương — nhóm components + số dư phép (4.9, 23§23.4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.annual_leave_ledger import annual_leave_remaining
from app.modules.attendance.models import LeaveType, PayPeriod, TimesheetMonth
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from app.modules.payroll.payslip_components import list_payslip_components
from app.modules.payroll.payslip_out import payslip_out as _payslip_out
from app.modules.payroll.schemas import HRPayslipDetailOut, PayslipComponentOut

DEDUCTION_CODES = frozenset({"BHXH", "BHYT", "BHTN", "UNION", "PIT", "ADVANCE"})
WORK_CODES = frozenset({"WD", "OT"})


def _leave_codes(db: Session) -> frozenset[str]:
    rows = db.query(LeaveType.code).all()
    return frozenset(r[0] for r in rows)


def _classify(code: str, kind: str, leave_codes: frozenset[str]) -> str:
    if kind == "deduction" or code in DEDUCTION_CODES:
        return "deduction"
    if code in WORK_CODES or code in leave_codes:
        return "work"
    return "allowance"


def _component_out(row, pc) -> PayslipComponentOut:
    return PayslipComponentOut(
        id=row.id,
        payslip_id=row.payslip_id,
        component_code=row.component_code,
        component_name=pc.name,
        segment=row.segment,
        seq_no=row.seq_no,
        quantity=row.quantity,
        unit=row.unit,
        unit_amount=row.unit_amount,
        amount=row.amount,
        note=row.note,
        sort_order=row.sort_order,
        kind=pc.kind,
    )


def get_hr_payslip_detail(db: Session, payslip_id: UUID) -> HRPayslipDetailOut:
    row = (
        db.query(Payslip, Employee, TimesheetMonth, PayPeriod)
        .join(Employee, Employee.id == Payslip.employee_id)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .filter(Payslip.id == payslip_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy phiếu lương.",
        )
    slip, emp, ts, pay = row
    period = f"{pay.year:04d}-{pay.month:02d}"
    leave_codes = _leave_codes(db)
    work_lines: list[PayslipComponentOut] = []
    allowance_lines: list[PayslipComponentOut] = []
    deduction_lines: list[PayslipComponentOut] = []
    for comp_row, pc in list_payslip_components(db, payslip_id):
        out = _component_out(comp_row, pc)
        bucket = _classify(comp_row.component_code, pc.kind, leave_codes)
        if bucket == "work":
            work_lines.append(out)
        elif bucket == "deduction":
            deduction_lines.append(out)
        else:
            allowance_lines.append(out)

    al_remaining = annual_leave_remaining(db, emp.id, pay.date_to or date.today())

    return HRPayslipDetailOut(
        payslip=_payslip_out(
            slip,
            emp,
            worked_days=ts.worked_days if ts else None,
            al_days=ts.al_days if ts else None,
            rem_days=ts.rem_days if ts else None,
            salary_divisor=pay.salary_divisor,
            period=period,
        ),
        period=period,
        work_lines=work_lines,
        allowance_lines=allowance_lines,
        deduction_lines=deduction_lines,
        annual_leave_remaining=al_remaining,
    )


def prev_period_label(period: str) -> str | None:
    year = int(period[:4])
    month = int(period[5:7])
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def prev_net_by_employee(db: Session, period: str) -> dict[UUID, Decimal]:
    prev = prev_period_label(period)
    if prev is None:
        return {}
    pay = db.query(PayPeriod).filter(PayPeriod.year == int(prev[:4]), PayPeriod.month == int(prev[5:7])).first()
    if pay is None:
        return {}
    rows = db.query(Payslip.employee_id, Payslip.net).filter(Payslip.pay_period_id == pay.id).all()
    return {emp_id: net for emp_id, net in rows}
