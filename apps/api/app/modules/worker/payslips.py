"""Worker phiếu lương: xem (P4.1) + xác nhận khóa (P4.2) — không AI."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from app.modules.payroll.payslip_detail import group_payslip_money_lines
from app.modules.worker.schemas import WorkerPayslipDetailOut, WorkerPayslipListOut

# CN chỉ thấy phiếu đã phát hành trở đi — không thấy draft
VISIBLE = ("published", "confirmed", "disputed", "resolved", "expired")


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


def _fallback_money_lines(slip: Payslip) -> tuple[list[dict], list[dict], list[dict]]:
    """Hồi quy khi chưa có payslip_components — tách work / allowance / deduction."""
    work = [
        {"label": "Lương ngày công", "amount": slip.wd_salary},
        {"label": "Tăng ca (OT)", "amount": slip.ot_pay},
    ]
    allowance = [
        {"label": "Phụ cấp", "amount": slip.allowance_total},
        {"label": "Điều chỉnh khác", "amount": slip.other_adjustments},
    ]
    deductions = [
        {"label": "BHXH", "amount": slip.bhxh},
        {"label": "BHYT", "amount": slip.bhyt},
        {"label": "BHTN", "amount": slip.bhtn},
        {"label": "Công đoàn", "amount": slip.union_fee},
        {"label": "Khấu trừ khác", "amount": slip.other_deductions},
        {"label": "TNCN", "amount": slip.pit_amount},
    ]
    return work, allowance, deductions


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
    if db is not None:
        grouped = group_payslip_money_lines(db, slip.id)
    else:
        grouped = None
    if grouped:
        work, allowance, deductions = grouped
    else:
        work, allowance, deductions = _fallback_money_lines(slip)
    can_confirm, can_dispute = _action_flags(slip)
    return WorkerPayslipDetailOut(
        id=slip.id,
        period=f"{pay.year:04d}-{pay.month:02d}",
        status=slip.status,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        net=slip.net,
        gross=slip.gross,
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
        worked_days=ts.worked_days if ts else None,
        al_days=ts.al_days if ts else None,
        rem_days=ts.rem_days if ts else None,
        confirm_deadline=slip.confirm_deadline,
        confirmed_at=slip.confirmed_at,
        work_lines=work,
        allowance_lines=allowance,
        deduction_lines=deductions,
        can_confirm=can_confirm,
        can_dispute=can_dispute,
        message=_detail_message(slip),
    )
