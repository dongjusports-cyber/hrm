"""Tính lương kỳ — P3.1 wd_salary + P3.2 allowances/chuyên cần."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.models import (
    AttendanceDay,
    LeaveType,
    PayPeriod,
    TimesheetAdjustment,
    TimesheetMonth,
    TimesheetMonthDetail,
)
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets, seed_leave_types
from app.modules.calendar.models import Holiday
from app.modules.calendar.service import get_work_week
from app.modules.mdm.models import Employee
from app.modules.mdm.service import resolve_tax_dependent_count
from app.modules.payroll.engine_allowances import (
    AllowanceInput,
    AllowanceTypeView,
    compute_allowances,
    should_zero_probation_allowances,
)
from app.modules.payroll.engine_insurance import InsuranceInput, compute_insurance_and_net
from app.modules.payroll.engine_leave_pay import (
    LeavePayInput,
    LeaveTypePayMeta,
    compute_leave_pay,
)
from app.modules.payroll.engine_ot import OtHours, OtInput, compute_ot_pay
from app.modules.payroll.engine_wd import WdSalaryInput, compute_wd_salary
from app.modules.payroll.adjustments import sums_for_employee
from app.modules.payroll.employee_bonuses import get_bonus_for_period, mark_bonuses_applied
from app.modules.payroll.attendance_penalty import (
    AttendanceDayPenaltyView,
    LeaveAdjustmentView,
    summarize_attendance_penalties,
)
from app.modules.payroll.models import (
    EmployeeAllowanceAssignment,
    PayComponent,
    PayrollRun,
    Payslip,
    PayslipComponent,
    PolicySnapshot,
)
from app.modules.payroll.money import D, ZERO, money_vnd
from app.modules.payroll.payslip_detail import get_hr_payslip_detail, prev_net_by_employee
from app.modules.payroll.period_eligibility import employee_on_payroll_period
from app.modules.payroll.payslip_components import (
    build_component_drafts,
    list_payslip_components,
    replace_payslip_components,
)
from app.modules.audit.service import write_audit
from app.modules.core.models import User
from app.modules.payroll.schemas import (
    CalculateResult,
    HRPayslipDetailOut,
    PayrollRunOut,
    PayslipComponentOut,
    PayslipOut,
)
from app.modules.payroll.seed_allowances import seed_allowance_types
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload


def _purge_ineligible_draft_payslips(db: Session, pay: PayPeriod) -> int:
    """Xóa phiếu nháp của NV không thuộc kỳ (vd. đã nghỉ trước kỳ)."""
    rows = (
        db.query(Payslip, Employee)
        .join(Employee, Employee.id == Payslip.employee_id)
        .filter(Payslip.pay_period_id == pay.id, Payslip.status == "draft")
        .all()
    )
    removed = 0
    for slip, emp in rows:
        if employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            continue
        db.query(PayslipComponent).filter(PayslipComponent.payslip_id == slip.id).delete(
            synchronize_session=False
        )
        db.delete(slip)
        removed += 1
    return removed


def _active_policy(db: Session) -> tuple[PolicyPackage | None, dict]:
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        return pkg, dict(pkg.payload)
    return None, default_payload()


from app.modules.payroll.payslip_out import payslip_out as _payslip_out


def _sal_allow_monthly(monthly: dict[str, Decimal]) -> Decimal:
    """Phụ cấp lương (Genus SAL_ALLOW) — cộng cơ sở WD/nghỉ, khác TRANSPORT prorate."""
    return D(monthly.get("SAL_ALLOW", ZERO))


def _leave_days_by_code(
    db: Session,
    pay_period_id: UUID,
    employee_id: UUID,
    timesheet_month_id: UUID,
) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for r in (
        db.query(TimesheetMonthDetail)
        .filter(
            TimesheetMonthDetail.timesheet_month_id == timesheet_month_id,
            TimesheetMonthDetail.category.like("ABS_%"),
        )
        .all()
    ):
        if r.days is not None and D(r.days) > 0:
            code = r.category[4:]
            out[code] = out.get(code, ZERO) + D(r.days)
    if out:
        return out
    for r in (
        db.query(TimesheetAdjustment)
        .filter(
            TimesheetAdjustment.pay_period_id == pay_period_id,
            TimesheetAdjustment.employee_id == employee_id,
            TimesheetAdjustment.kind == "leave",
        )
        .all()
    ):
        if r.leave_code and r.days is not None:
            code = r.leave_code.strip().upper()
            out[code] = out.get(code, ZERO) + D(r.days)
    return out


def _detail_days_by_category(db: Session, timesheet_month_id: UUID) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for r in (
        db.query(TimesheetMonthDetail)
        .filter(TimesheetMonthDetail.timesheet_month_id == timesheet_month_id)
        .all()
    ):
        if r.days is not None and D(r.days) > 0:
            out[r.category] = out.get(r.category, ZERO) + D(r.days)
    return out


def _leave_type_pay_meta(db: Session) -> dict[str, LeaveTypePayMeta]:
    seed_leave_types(db)
    return {
        r.code: LeaveTypePayMeta(
            code=r.code,
            name=r.name,
            pay_ratio_percent=r.pay_ratio_percent,
        )
        for r in db.query(LeaveType).all()
    }


def _attendance_day_views(
    db: Session,
    employee_id: UUID,
    date_from: date,
    date_to: date,
) -> list[AttendanceDayPenaltyView]:
    rows = (
        db.query(AttendanceDay)
        .filter(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.work_date >= date_from,
            AttendanceDay.work_date <= date_to,
        )
        .order_by(AttendanceDay.work_date.asc())
        .all()
    )
    return [
        AttendanceDayPenaltyView(
            work_date=r.work_date,
            is_workday=bool(r.is_workday),
            leave_code=r.leave_code,
            late_minutes=int(r.late_minutes or 0),
            early_minutes=int(r.early_minutes or 0),
            punch_count=int(r.punch_count or 0),
            first_in=r.first_in,
            last_out=r.last_out,
            worked_hours=D(r.worked_hours),
        )
        for r in rows
    ]


def _leave_adjustment_views(
    db: Session,
    pay_period_id: UUID,
    employee_id: UUID,
) -> list[LeaveAdjustmentView]:
    rows = (
        db.query(TimesheetAdjustment)
        .filter(
            TimesheetAdjustment.pay_period_id == pay_period_id,
            TimesheetAdjustment.employee_id == employee_id,
            TimesheetAdjustment.kind == "leave",
        )
        .all()
    )
    out: list[LeaveAdjustmentView] = []
    for r in rows:
        if r.leave_code and r.days is not None and D(r.days) > 0:
            out.append(LeaveAdjustmentView(leave_code=r.leave_code, days=D(r.days)))
    return out


def _penalty_summary_for_employee(
    db: Session,
    pay,
    emp: Employee,
    policy: dict,
):
    days = _attendance_day_views(db, emp.id, pay.date_from, pay.date_to)
    adjs = _leave_adjustment_views(db, pay.id, emp.id)
    penalties = policy.get("attendance_penalties") or {}
    return summarize_attendance_penalties(
        days,
        adjs,
        contract_signed_at=emp.contract_signed_at,
        penalties=penalties,
    )


def _monthly_map(db: Session, emp_id: UUID) -> dict[str, Decimal]:
    rows = (
        db.query(EmployeeAllowanceAssignment, PayComponent)
        .join(PayComponent, PayComponent.id == EmployeeAllowanceAssignment.allowance_type_id)
        .filter(EmployeeAllowanceAssignment.employee_id == emp_id, PayComponent.is_active.is_(True))
        .all()
    )
    out: dict[str, Decimal] = {}
    for asg, at in rows:
        out[at.code] = D(asg.amount) if asg.amount is not None else D(at.default_amount)
    return out


def _type_views(db: Session) -> list[AllowanceTypeView]:
    seed_allowance_types(db)
    rows = db.query(PayComponent).filter(PayComponent.is_active.is_(True)).all()
    return [
        AllowanceTypeView(
            code=r.code,
            name=r.name,
            proration=r.proration,
            include_in_si_base=r.include_in_si_base,
            include_in_ot_base=r.include_in_ot_base,
            default_amount=r.default_amount,
            rules=r.rules if isinstance(r.rules, dict) else None,
        )
        for r in rows
    ]


@dataclass(frozen=True)
class EmployeePayslipCalc:
    wd_salary: Decimal
    allowance_total: Decimal
    ot_pay: Decimal
    other_adjustments: Decimal
    other_deductions: Decimal
    gross: Decimal
    taxable_income: Decimal
    bhxh: Decimal
    bhyt: Decimal
    bhtn: Decimal
    union_fee: Decimal
    pit_amount: Decimal
    net: Decimal
    bonus_total: Decimal


def compute_employee_payslip(
    db: Session,
    pay: PayPeriod,
    emp: Employee,
    ts: TimesheetMonth,
    payload: dict,
) -> EmployeePayslipCalc:
    """Tính phiếu một NV — không ghi DB (dùng calculate + simulate 4.10)."""
    rule = get_work_week(db)
    holidays = frozenset(h.date for h in db.query(Holiday).all())
    work_weekdays = tuple(int(x) for x in rule.work_weekdays)
    type_views = _type_views(db)
    leave_types = _leave_type_pay_meta(db)
    monthly = _monthly_map(db, emp.id)
    sal_allow = _sal_allow_monthly(monthly)
    leave_days = _leave_days_by_code(db, pay.id, emp.id, ts.id)
    detail_days = _detail_days_by_category(db, ts.id)
    wd_inp = WdSalaryInput(
        contract_salary=emp.contract_salary,
        probation_salary=emp.probation_salary,
        salary_divisor=pay.salary_divisor,
        worked_days=ts.worked_days,
        al_days=ts.al_days,
        period_from=pay.date_from,
        period_to=pay.date_to,
        contract_signed_at=emp.contract_signed_at,
        work_weekdays=work_weekdays,
        holiday_dates=holidays,
        sal_allow=sal_allow,
    )
    wd_res = compute_wd_salary(wd_inp)
    leave_res = compute_leave_pay(
        LeavePayInput(
            contract_salary=emp.contract_salary,
            probation_salary=emp.probation_salary,
            sal_allow=sal_allow,
            salary_divisor=pay.salary_divisor,
            wd_context=wd_inp,
            leave_days_by_code=leave_days,
            leave_types=leave_types,
        )
    )
    penalty_sum = _penalty_summary_for_employee(db, pay, emp, payload)
    allow_res = compute_allowances(
        AllowanceInput(
            salary_divisor=pay.salary_divisor,
            worked_days=ts.worked_days,
            late_count=penalty_sum.late_count,
            early_count=penalty_sum.early_count,
            penalty_absent_days=penalty_sum.penalty_absent_days,
            join_date=emp.join_date,
            as_of=pay.date_to,
            policy=payload,
            monthly_by_code=monthly,
            types=type_views,
            child_count_under_6=0,
            leave_days_by_code=leave_days,
            detail_days_by_category=detail_days,
            penalty_audit=penalty_sum.detail,
            suppress_allowances=should_zero_probation_allowances(
                payload,
                contract_signed_at=emp.contract_signed_at,
                period_to=pay.date_to,
            ),
        )
    )
    ot_res = compute_ot_pay(
        OtInput(
            contract_salary=emp.contract_salary,
            salary_divisor=pay.salary_divisor,
            allowance_lines=allow_res.lines,
            attend_full_monthly=allow_res.attend_full_monthly,
            hours=OtHours(
                weekday=D(ts.ot_hours_weekday),
                weekend=D(ts.ot_hours_weekend),
                holiday=D(ts.ot_hours_holiday),
            ),
            policy=payload,
        )
    )
    # ot_hours_external → bảng OT ngoài (ATM), không cộng gross — xem payroll.ot_external
    other_adj, other_ded, _adj_detail = sums_for_employee(db, pay.id, emp.id)
    bonus_res = get_bonus_for_period(db, emp.id, pay.id)
    gross = money_vnd(
        wd_res.wd_salary
        + leave_res.leave_pay_total
        + allow_res.allowance_total
        + ot_res.ot_pay
        + other_adj
        + bonus_res.total
    )
    dep_count = resolve_tax_dependent_count(db, emp.id, as_of=pay.date_to)
    ins_res = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=ot_res.si_contribution_base,
            si_enrolled=bool(emp.si_enrolled),
            si_base_override=emp.si_base_override,
            union_fee_override=emp.union_fee_override,
            gross=gross,
            other_deductions=other_ded,
            other_adjustments=other_adj,
            policy=payload,
            tax_dependent_count=dep_count,
            pit_enrolled=bool(getattr(emp, "pit_enrolled", True)),
        )
    )
    return EmployeePayslipCalc(
        wd_salary=wd_res.wd_salary,
        allowance_total=allow_res.allowance_total,
        ot_pay=ot_res.ot_pay,
        other_adjustments=other_adj,
        other_deductions=other_ded,
        gross=gross,
        taxable_income=ins_res.taxable_income,
        bhxh=ins_res.bhxh,
        bhyt=ins_res.bhyt,
        bhtn=ins_res.bhtn,
        union_fee=ins_res.union_fee,
        pit_amount=ins_res.pit_amount,
        net=ins_res.net,
        bonus_total=bonus_res.total,
    )


def calculate_period(db: Session, period: str, *, actor: User | None = None) -> CalculateResult:
    pay = ensure_pay_period(db, period)
    if pay.status == "locked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: kỳ lương đã khóa — không tính lại.",
        )
    if pay.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Trợ Lý AI: kỳ đã phát hành — không tính lại. "
                "Admin dùng «Mở lại để tính» rồi tính lương."
            ),
        )

    rebuild_timesheets(db, period, recalc_days=True)
    pay = ensure_pay_period(db, period)
    _purge_ineligible_draft_payslips(db, pay)

    pkg, payload = _active_policy(db)
    snapshot = PolicySnapshot(
        pay_period_id=pay.id,
        package_id=pkg.id if pkg else None,
        payload=payload,
    )
    db.add(snapshot)
    db.flush()

    run = PayrollRun(
        pay_period_id=pay.id,
        status="running",
        started_at=datetime.now(timezone.utc),
        policy_snapshot_id=snapshot.id,
        message="Đang tính wd_salary + phụ cấp…",
    )
    db.add(run)
    db.flush()

    rule = get_work_week(db)
    holidays = frozenset(h.date for h in db.query(Holiday).all())
    work_weekdays = tuple(int(x) for x in rule.work_weekdays)
    type_views = _type_views(db)
    leave_types = _leave_type_pay_meta(db)

    timesheets = (
        db.query(TimesheetMonth, Employee)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(TimesheetMonth.pay_period_id == pay.id, Employee.deleted_at.is_(None))
        .all()
    )

    computed = 0
    for ts, emp in timesheets:
        if not employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            continue
        slip = (
            db.query(Payslip)
            .filter(Payslip.pay_period_id == pay.id, Payslip.employee_id == emp.id)
            .one_or_none()
        )
        if slip is not None and slip.status in ("published", "confirmed", "locked"):
            continue

        monthly = _monthly_map(db, emp.id)
        sal_allow = _sal_allow_monthly(monthly)
        leave_days = _leave_days_by_code(db, pay.id, emp.id, ts.id)
        detail_days = _detail_days_by_category(db, ts.id)

        wd_inp = WdSalaryInput(
            contract_salary=emp.contract_salary,
            probation_salary=emp.probation_salary,
            salary_divisor=pay.salary_divisor,
            worked_days=ts.worked_days,
            al_days=ts.al_days,
            period_from=pay.date_from,
            period_to=pay.date_to,
            contract_signed_at=emp.contract_signed_at,
            work_weekdays=work_weekdays,
            holiday_dates=holidays,
            sal_allow=sal_allow,
        )
        wd_res = compute_wd_salary(wd_inp)
        leave_res = compute_leave_pay(
            LeavePayInput(
                contract_salary=emp.contract_salary,
                probation_salary=emp.probation_salary,
                sal_allow=sal_allow,
                salary_divisor=pay.salary_divisor,
                wd_context=wd_inp,
                leave_days_by_code=leave_days,
                leave_types=leave_types,
            )
        )
        penalty_sum = _penalty_summary_for_employee(db, pay, emp, payload)
        allow_res = compute_allowances(
            AllowanceInput(
                salary_divisor=pay.salary_divisor,
                worked_days=ts.worked_days,
                late_count=penalty_sum.late_count,
                early_count=penalty_sum.early_count,
                penalty_absent_days=penalty_sum.penalty_absent_days,
                join_date=emp.join_date,
                as_of=pay.date_to,
                policy=payload,
                monthly_by_code=monthly,
                types=type_views,
                child_count_under_6=0,
                leave_days_by_code=leave_days,
                detail_days_by_category=detail_days,
                penalty_audit=penalty_sum.detail,
                suppress_allowances=should_zero_probation_allowances(
                    payload,
                    contract_signed_at=emp.contract_signed_at,
                    period_to=pay.date_to,
                ),
            )
        )
        ot_res = compute_ot_pay(
            OtInput(
                contract_salary=emp.contract_salary,
                salary_divisor=pay.salary_divisor,
                allowance_lines=allow_res.lines,
                attend_full_monthly=allow_res.attend_full_monthly,
                hours=OtHours(
                    weekday=D(ts.ot_hours_weekday),
                    weekend=D(ts.ot_hours_weekend),
                    holiday=D(ts.ot_hours_holiday),
                ),
                policy=payload,
            )
        )
        other_adj, other_ded, adj_detail = sums_for_employee(db, pay.id, emp.id)
        bonus_res = get_bonus_for_period(db, emp.id, pay.id)
        gross = money_vnd(
            wd_res.wd_salary
            + leave_res.leave_pay_total
            + allow_res.allowance_total
            + ot_res.ot_pay
            + other_adj
            + bonus_res.total
        )
        dep_count = resolve_tax_dependent_count(db, emp.id, as_of=pay.date_to)
        ins_res = compute_insurance_and_net(
            InsuranceInput(
                si_contribution_base=ot_res.si_contribution_base,
                si_enrolled=bool(emp.si_enrolled),
                si_base_override=emp.si_base_override,
                union_fee_override=emp.union_fee_override,
                gross=gross,
                other_deductions=other_ded,
                other_adjustments=other_adj,
                policy=payload,
                tax_dependent_count=dep_count,
                pit_enrolled=bool(getattr(emp, "pit_enrolled", True)),
            )
        )

        if slip is None:
            slip = Payslip(pay_period_id=pay.id, employee_id=emp.id)
            db.add(slip)

        slip.policy_snapshot_id = snapshot.id
        slip.wd_salary = wd_res.wd_salary
        slip.allowance_total = allow_res.allowance_total
        slip.ot_pay = ot_res.ot_pay
        slip.other_adjustments = other_adj
        slip.gross = gross
        slip.taxable_income = ins_res.taxable_income
        slip.bhxh = ins_res.bhxh
        slip.bhyt = ins_res.bhyt
        slip.bhtn = ins_res.bhtn
        slip.union_fee = ins_res.union_fee
        slip.other_deductions = ins_res.other_deductions
        slip.pit_amount = ins_res.pit_amount
        slip.net = ins_res.net
        slip.status = "draft"
        slip.lines = {
            "phase": "P4.8+bonus",
            "wd": wd_res.detail,
            "leave_pay": leave_res.detail,
            "attendance_penalty": penalty_sum.detail,
            "allowances": allow_res.detail,
            "attend_keep_percent": allow_res.attend_keep_percent,
            "attend_full_monthly": str(allow_res.attend_full_monthly),
            "ot": ot_res.detail,
            "bonus": {
                "total": str(bonus_res.total),
                "lines": [
                    {
                        "code": ln.bonus_code,
                        "seq_times": ln.seq_times,
                        "amount": str(ln.amount),
                        "reason": ln.reason,
                    }
                    for ln in bonus_res.lines
                ],
            },
            "si_contribution_base": str(ot_res.si_contribution_base),
            "insurance": ins_res.detail,
            "adjustments": adj_detail,
            "other_adjustments": str(other_adj),
            "other_deductions": str(other_ded),
            "note": "WD + lương nghỉ + PC + OT + điều chỉnh + BH/CD + TNCN(policy) → net.",
        }
        db.flush()
        replace_payslip_components(
            db,
            slip.id,
            build_component_drafts(
                wd_inp=wd_inp,
                wd_res=wd_res,
                leave_res=leave_res,
                allow_res=allow_res,
                ot_res=ot_res,
                ins_res=ins_res,
                adj_detail=adj_detail,
                bonus_res=bonus_res,
            ),
        )
        mark_bonuses_applied(db, emp.id, pay.id)
        computed += 1

    _purge_ineligible_draft_payslips(db, pay)

    run.employee_count = computed
    run.status = "success"
    run.finished_at = datetime.now(timezone.utc)
    pit_on = bool((payload or {}).get("pit_enabled", False))
    run.message = (
        f"Đã tính đủ phiếu (WD+nghỉ+PC+OT+BH/CD"
        f"{'+TNCN' if pit_on else ''}→net) cho {computed} NV kỳ {period} "
        f"(divisor={pay.salary_divisor})."
    )
    if pay.status == "open":
        pay.status = "calculating"
    db.commit()
    db.refresh(run)
    if actor is not None:
        write_audit(
            db,
            actor=actor,
            action="payroll.calculate",
            entity_type="pay_period",
            entity_id=period,
            summary=f"Tính lương kỳ {period}: {computed} NV",
            meta={"employee_count": computed, "divisor": str(pay.salary_divisor)},
        )

    slips = (
        db.query(Payslip, Employee, TimesheetMonth)
        .join(Employee, Employee.id == Payslip.employee_id)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .filter(Payslip.pay_period_id == pay.id)
        .order_by(Employee.employee_code)
        .all()
    )
    prev_map = prev_net_by_employee(db, period)
    payslips = [
        _payslip_out(
            s,
            e,
            worked_days=t.worked_days if t else None,
            al_days=t.al_days if t else None,
            rem_days=t.rem_days if t else None,
            salary_divisor=pay.salary_divisor,
            period=period,
            prev_net=prev_map.get(s.employee_id),
        )
        for s, e, t in slips
        if employee_on_payroll_period(e, pay.date_from, pay.date_to)
    ]

    return CalculateResult(
        run=PayrollRunOut.model_validate(run),
        payslips=payslips,
        message=run.message,
    )


def list_payslips(db: Session, period: str) -> list[PayslipOut]:
    pay = ensure_pay_period(db, period)
    prev_map = prev_net_by_employee(db, period)
    rows = (
        db.query(Payslip, Employee, TimesheetMonth)
        .join(Employee, Employee.id == Payslip.employee_id)
        .outerjoin(
            TimesheetMonth,
            (TimesheetMonth.pay_period_id == Payslip.pay_period_id)
            & (TimesheetMonth.employee_id == Payslip.employee_id),
        )
        .filter(Payslip.pay_period_id == pay.id)
        .order_by(Employee.employee_code)
        .all()
    )
    return [
        _payslip_out(
            s,
            e,
            worked_days=t.worked_days if t else None,
            al_days=t.al_days if t else None,
            rem_days=t.rem_days if t else None,
            salary_divisor=pay.salary_divisor,
            period=period,
            prev_net=prev_map.get(s.employee_id),
        )
        for s, e, t in rows
        if employee_on_payroll_period(e, pay.date_from, pay.date_to)
    ]


def get_hr_payslip(db: Session, payslip_id: UUID) -> HRPayslipDetailOut:
    return get_hr_payslip_detail(db, payslip_id)


def get_payslip_components(db: Session, payslip_id: UUID) -> list[PayslipComponentOut]:
    slip = db.get(Payslip, payslip_id)
    if slip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy phiếu lương.",
        )
    rows = list_payslip_components(db, payslip_id)
    return [
        PayslipComponentOut(
            id=comp.id,
            payslip_id=comp.payslip_id,
            component_code=comp.component_code,
            component_name=pc.name,
            segment=comp.segment,
            seq_no=comp.seq_no,
            quantity=comp.quantity,
            unit=comp.unit,
            unit_amount=comp.unit_amount,
            amount=comp.amount,
            note=comp.note,
            sort_order=comp.sort_order,
            kind=pc.kind,
        )
        for comp, pc in rows
    ]
