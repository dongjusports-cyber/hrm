"""Worker phiếu lương: xem (P4.1) + xác nhận khóa (P4.2) — không AI."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.modules.attendance.annual_leave_ledger import annual_leave_remaining
from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.core.models import User
from app.modules.mdm.models import Employee, Team
from app.modules.payroll.models import Payslip
from app.modules.payroll.payslip_detail import (
    _day_target,
    _sum_line_amounts,
    group_payslip_worker_sections,
)
from app.modules.payroll.payslip_genus_template import (
    apply_genus_allowance_template,
    apply_genus_deduction_template,
    apply_genus_leave_template,
    apply_genus_work_template,
)
from app.modules.worker.schemas import PayslipLineOut, WorkerPayslipDetailOut, WorkerPayslipListOut

# CN chỉ thấy phiếu đã phát hành trở đi — không thấy draft
VISIBLE = ("published", "confirmed", "disputed", "resolved", "expired")

_EMPLOYEE_LOAD = (
    joinedload(Employee.team).joinedload(Team.department),
    joinedload(Employee.position),
)


def _require_employee(worker: User) -> UUID:
    if worker.employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, tài khoản chưa gắn hồ sơ nhân sự. Liên hệ HR.",
        )
    return worker.employee_id


def _expire_if_past_deadline(db: Session, slip: Payslip) -> None:
    """published quá hạn → expired (lazy, KISS — không cron)."""
    if slip.status != "published" or slip.confirm_deadline is None:
        return
    if date.today() > slip.confirm_deadline:
        slip.status = "expired"
        db.commit()
        db.refresh(slip)


def _action_flags(slip: Payslip) -> tuple[bool, bool]:
    open_for_worker = slip.status == "published"
    return open_for_worker, open_for_worker


def list_worker_payslips(db: Session, worker: User) -> list[WorkerPayslipListOut]:
    emp_id = _require_employee(worker)
    rows = (
        db.query(Payslip, PayPeriod)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .filter(Payslip.employee_id == emp_id, Payslip.status.in_(VISIBLE))
        .order_by(PayPeriod.year.desc(), PayPeriod.month.desc())
        .all()
    )
    out: list[WorkerPayslipListOut] = []
    dirty = False
    for slip, pay in rows:
        if slip.status == "published" and slip.confirm_deadline and date.today() > slip.confirm_deadline:
            slip.status = "expired"
            dirty = True
        out.append(
            WorkerPayslipListOut(
                id=slip.id,
                period=f"{pay.year:04d}-{pay.month:02d}",
                status=slip.status,
                net=slip.net,
                gross=slip.gross,
                confirm_deadline=slip.confirm_deadline,
            )
        )
    if dirty:
        db.commit()
    return out


def get_worker_payslip(db: Session, worker: User, payslip_id: UUID) -> WorkerPayslipDetailOut:
    emp_id = _require_employee(worker)
    row = (
        db.query(Payslip, PayPeriod, Employee, TimesheetMonth)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .options(_EMPLOYEE_LOAD)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .filter(Payslip.id == payslip_id, Payslip.employee_id == emp_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, không tìm thấy phiếu lương này.",
        )
    slip, pay, emp, ts = row
    if slip.status not in VISIBLE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, phiếu chưa được HR phát hành.",
        )

    _expire_if_past_deadline(db, slip)
    return _to_detail(slip, pay, emp, ts, db)


def confirm_worker_payslip(
    db: Session, worker: User, payslip_id: UUID
) -> WorkerPayslipDetailOut:
    """P4.2 — CN xác nhận → khóa phiếu (P8). Không khiếu nại nữa."""
    emp_id = _require_employee(worker)
    row = (
        db.query(Payslip, PayPeriod, Employee, TimesheetMonth)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .options(_EMPLOYEE_LOAD)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .filter(Payslip.id == payslip_id, Payslip.employee_id == emp_id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trợ Lý AI xin chào {worker.full_name}, không tìm thấy phiếu lương này.",
        )
    slip, pay, emp, ts = row
    _expire_if_past_deadline(db, slip)

    if slip.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, phiếu kỳ "
                f"{pay.year:04d}-{pay.month:02d} đã xác nhận và khóa."
            ),
        )
    if slip.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, đã quá hạn xác nhận phiếu này. "
                "Liên hệ HR nếu cần hỗ trợ."
            ),
        )
    if slip.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Trợ Lý AI xin chào {worker.full_name}, chỉ xác nhận được phiếu "
                "đang chờ xác nhận (đã phát hành)."
            ),
        )

    slip.status = "confirmed"
    slip.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(slip)
    return _to_detail(slip, pay, emp, ts, db)


def _line_out(raw: dict) -> PayslipLineOut:
    amt = raw.get("amount")
    return PayslipLineOut(
        label=raw["label"],
        amount=amt if amt is not None else None,
        quantity=raw.get("quantity"),
        unit=raw.get("unit"),
        target=raw.get("target"),
    )


def _fallback_worker_sections(
    slip: Payslip, pay: PayPeriod, ts: TimesheetMonth | None
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Hồi quy khi chưa có payslip_components."""
    divisor = pay.salary_divisor if pay.salary_divisor > 0 else None
    wd_qty = ts.worked_days if ts else None
    work = [
        {
            "label": "Lương ngày công",
            "amount": slip.wd_salary,
            "quantity": wd_qty,
            "unit": "day" if wd_qty is not None else None,
            "target": _day_target(divisor, "day"),
            "component_code": "WD",
            "note": None,
        },
        {
            "label": "Tăng ca (OT)",
            "amount": slip.ot_pay if slip.ot_pay > 0 else None,
            "quantity": None,
            "unit": "hour",
            "target": None,
            "component_code": "OT",
            "note": None,
        },
    ]
    leave: list[dict] = []
    if ts and ts.al_days and ts.al_days > 0:
        leave.append(
            {
                "label": "Nghỉ phép năm",
                "amount": None,
                "quantity": ts.al_days,
                "unit": "day",
                "target": _day_target(divisor, "day"),
                "component_code": "ALE",
                "note": None,
            }
        )
    allowance = [
        {
            "label": "Phụ cấp",
            "amount": slip.allowance_total,
            "quantity": None,
            "unit": None,
            "target": None,
            "component_code": "ATTEND",
            "note": None,
        },
        {
            "label": "Điều chỉnh khác",
            "amount": slip.other_adjustments if slip.other_adjustments != 0 else None,
            "quantity": None,
            "unit": None,
            "target": None,
            "component_code": "OTHER",
            "note": None,
        },
    ]
    deductions = [
        {"label": "BHXH", "amount": slip.bhxh, "quantity": None, "unit": None, "target": None, "component_code": "BHXH", "note": None},
        {"label": "BHYT", "amount": slip.bhyt, "quantity": None, "unit": None, "target": None, "component_code": "BHYT", "note": None},
        {"label": "BHTN", "amount": slip.bhtn, "quantity": None, "unit": None, "target": None, "component_code": "BHTN", "note": None},
        {"label": "Công đoàn", "amount": slip.union_fee, "quantity": None, "unit": None, "target": None, "component_code": "UNION", "note": None},
        {"label": "Khấu trừ khác", "amount": slip.other_deductions if slip.other_deductions > 0 else None, "quantity": None, "unit": None, "target": None, "component_code": "OTHER_DED", "note": None},
        {"label": "TNCN", "amount": slip.pit_amount if slip.pit_amount > 0 else None, "quantity": None, "unit": None, "target": None, "component_code": "PIT", "note": None},
    ]
    return work, leave, allowance, deductions


def _header_salary(value: Decimal) -> Decimal | None:
    return value if value > 0 else None


def _detail_message(slip: Payslip) -> str:
    if slip.status == "published":
        return "Bạn có thể xác nhận hoặc khiếu nại khi phiếu ở trạng thái đã phát hành."
    if slip.status == "confirmed":
        return "Bạn đã xác nhận phiếu này — phiếu đã khóa, không khiếu nại được nữa."
    if slip.status == "expired":
        return "Đã quá hạn xác nhận. Liên hệ HR nếu cần hỗ trợ."
    if slip.status == "disputed":
        return "Phiếu đang khiếu nại — chờ HR xử lý."
    return "Phiếu đã xử lý — xem chi tiết bên dưới."


def _to_detail(
    slip: Payslip, pay: PayPeriod, emp: Employee, ts: TimesheetMonth | None, db: Session | None = None
) -> WorkerPayslipDetailOut:
    divisor = pay.salary_divisor if pay.salary_divisor > 0 else None
    grouped = group_payslip_worker_sections(db, slip.id, divisor) if db is not None else None
    if grouped:
        work_raw, leave_raw, allowance_raw, deductions_raw = grouped
    else:
        work_raw, leave_raw, allowance_raw, deductions_raw = _fallback_worker_sections(slip, pay, ts)

    work_subtotal = _sum_line_amounts(work_raw)
    leave_subtotal = _sum_line_amounts(leave_raw)
    allowance_subtotal = _sum_line_amounts(allowance_raw)
    deduction_subtotal = _sum_line_amounts(deductions_raw)

    work = apply_genus_work_template(work_raw, divisor)
    leave = apply_genus_leave_template(leave_raw, divisor)
    allowance = apply_genus_allowance_template(allowance_raw, divisor)
    deductions = apply_genus_deduction_template(deductions_raw, divisor)

    dept = emp.department
    al_remaining = (
        annual_leave_remaining(db, emp.id, pay.date_to or date.today()) if db is not None else None
    )

    can_confirm, can_dispute = _action_flags(slip)
    return WorkerPayslipDetailOut(
        id=slip.id,
        period=f"{pay.year:04d}-{pay.month:02d}",
        status=slip.status,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        department_name=dept.name if dept else None,
        team_name=emp.team.name if emp.team else None,
        position_title=emp.position_title or (emp.position.name if emp.position else None),
        probation_salary=_header_salary(emp.probation_salary),
        contract_salary=_header_salary(emp.contract_salary),
        net=slip.net,
        gross=slip.gross,
        taxable_income=slip.taxable_income,
        wd_salary=slip.wd_salary,
        allowance_total=slip.allowance_total,
        ot_pay=slip.ot_pay,
        other_adjustments=slip.other_adjustments,
        bhxh=slip.bhxh,
        bhyt=slip.bhyt,
        bhtn=slip.bhtn,
        union_fee=slip.union_fee,
        other_deductions=slip.other_deductions,
        pit_amount=slip.pit_amount,
        salary_divisor=divisor,
        worked_days=ts.worked_days if ts else None,
        al_days=ts.al_days if ts else None,
        rem_days=ts.rem_days if ts else None,
        work_subtotal=work_subtotal,
        leave_subtotal=leave_subtotal,
        allowance_subtotal=allowance_subtotal,
        deduction_subtotal=deduction_subtotal,
        annual_leave_entitled=None,
        annual_leave_used=None,
        annual_leave_remaining=al_remaining,
        confirm_deadline=slip.confirm_deadline,
        confirmed_at=slip.confirmed_at,
        work_lines=[_line_out(ln) for ln in work],
        leave_lines=[_line_out(ln) for ln in leave],
        allowance_lines=[_line_out(ln) for ln in allowance],
        deduction_lines=[_line_out(ln) for ln in deductions],
        can_confirm=can_confirm,
        can_dispute=can_dispute,
        message=_detail_message(slip),
    )
