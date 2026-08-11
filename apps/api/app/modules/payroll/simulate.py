"""4.10 — Chạy thử lương: so sánh gói chính sách, không ghi CSDL."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.mdm.models import Department, Employee, Team
from app.modules.payroll.models import Payslip
from app.modules.payroll.money import D, ZERO
from app.modules.payroll.schemas import (
    PayslipAmountsOut,
    PolicyOptionOut,
    SimulateRequest,
    SimulateResult,
    SimulateRowOut,
)
from app.modules.payroll.service import _active_policy, compute_employee_payslip
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload


def list_policy_options(db: Session) -> list[PolicyOptionOut]:
    rows = db.query(PolicyPackage).order_by(PolicyPackage.effective_from.desc()).all()
    return [
        PolicyOptionOut(
            id=r.id,
            name=r.name,
            effective_from=r.effective_from,
            is_active=bool(r.is_active),
        )
        for r in rows
    ]


def _resolve_policy(
    db: Session, package_id: UUID | None
) -> tuple[PolicyPackage | None, dict]:
    if package_id is None:
        return _active_policy(db)
    pkg = db.get(PolicyPackage, package_id)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy gói chính sách.",
        )
    payload = dict(pkg.payload) if isinstance(pkg.payload, dict) else default_payload()
    return pkg, payload


def _amounts_from_slip(slip: Payslip | None) -> PayslipAmountsOut | None:
    if slip is None:
        return None
    bonus_total = ZERO
    if isinstance(slip.lines, dict):
        bonus = slip.lines.get("bonus") or {}
        if isinstance(bonus, dict) and bonus.get("total") is not None:
            bonus_total = D(bonus["total"])
    return PayslipAmountsOut(
        wd_salary=slip.wd_salary,
        allowance_total=slip.allowance_total,
        ot_pay=slip.ot_pay,
        gross=slip.gross,
        pit_amount=slip.pit_amount,
        net=slip.net,
        bonus_total=bonus_total,
    )


def _amounts_from_calc(calc) -> PayslipAmountsOut:
    return PayslipAmountsOut(
        wd_salary=calc.wd_salary,
        allowance_total=calc.allowance_total,
        ot_pay=calc.ot_pay,
        gross=calc.gross,
        pit_amount=calc.pit_amount,
        net=calc.net,
        bonus_total=calc.bonus_total,
    )


def simulate_period(db: Session, body: SimulateRequest) -> SimulateResult:
    """Tính thử theo gói chính sách — chỉ đọc CSDL, không commit thay đổi."""
    pay = ensure_pay_period(db, body.period)
    pkg, payload = _resolve_policy(db, body.policy_package_id)

    q = (
        db.query(TimesheetMonth, Employee)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(
            TimesheetMonth.pay_period_id == pay.id,
            Employee.deleted_at.is_(None),
        )
    )

    scope = (body.scope or "all").strip().lower()
    if scope == "department":
        if body.department_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: chọn bộ phận khi phạm vi «Theo bộ phận».",
            )
        q = q.join(Team, Team.id == Employee.team_id).join(
            Department, Department.id == Team.department_id
        ).filter(Department.id == body.department_id)
    elif scope == "team":
        if body.team_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: chọn tổ khi phạm vi «Theo tổ».",
            )
        q = q.filter(Employee.team_id == body.team_id)
    elif scope == "employees":
        codes = [c.strip() for c in (body.employee_codes or []) if c and c.strip()]
        if not codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: nhập ít nhất một MSNV.",
            )
        q = q.filter(Employee.employee_code.in_(codes))
    elif scope != "all":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: phạm vi không hợp lệ (all | department | team | employees).",
        )

    q = q.order_by(Employee.employee_code.asc())
    rows_out: list[SimulateRowOut] = []

    for ts, emp in q.all():
        slip = (
            db.query(Payslip)
            .filter(Payslip.pay_period_id == pay.id, Payslip.employee_id == emp.id)
            .one_or_none()
        )
        current = _amounts_from_slip(slip)
        calc = compute_employee_payslip(db, pay, emp, ts, payload)
        simulated = _amounts_from_calc(calc)
        cur_net = current.net if current else D("0")
        rows_out.append(
            SimulateRowOut(
                employee_id=emp.id,
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                current=current,
                simulated=simulated,
                delta_net=simulated.net - cur_net,
            )
        )

    pkg_name = pkg.name if pkg else "Mặc định (seed)"
    changed = sum(1 for r in rows_out if r.delta_net != 0)
    return SimulateResult(
        period=body.period,
        policy_package_id=pkg.id if pkg else None,
        policy_package_name=pkg_name,
        employee_count=len(rows_out),
        rows=rows_out,
        message=(
            f"Chạy thử {len(rows_out)} NV — gói «{pkg_name}». "
            f"{changed} NV có Thực lãnh khác số hiện tại. Không ghi CSDL."
        ),
    )
