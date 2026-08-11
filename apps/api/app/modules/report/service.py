"""Tính KPI kỳ lương — P5.1."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException, status
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.modules.ai.models import AiAlert
from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.core.models import User
from app.modules.dispute.models import Dispute
from app.modules.dispute.service import OPEN_STATUSES
from app.modules.mdm.models import Department, Employee
from app.modules.payroll.models import Payslip
from app.modules.payroll.money import D, ZERO
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload
from app.modules.report import engine
from app.modules.report.schemas import (
    DeptKpiRow,
    KpiPeriodOut,
    ManpowerBucket,
    OverviewOut,
    TodoCardOut,
)

CATEGORY_LABELS = {
    "direct": "Direct",
    "prod_indirect": "Prod Indirect",
    "admin_indirect": "Admin Indirect",
}


def user_can_view_reports(user: User) -> bool:
    if user.role == "admin":
        return True
    return user.has_module("report") or user.has_module("overview")


def _active_policy(db: Session) -> dict:
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        return dict(pkg.payload)
    return default_payload()


def _period_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _was_on_payroll(emp: Employee, start: date, end: date) -> bool:
    """NV thuộc kỳ: đã vào trước/trong kỳ và chưa nghỉ trước kỳ."""
    if emp.deleted_at is not None:
        return False
    if emp.join_date and emp.join_date > end:
        return False
    if emp.resign_date and emp.resign_date < start:
        return False
    return True


def compute_kpi(db: Session, period: str) -> KpiPeriodOut:
    pay = ensure_pay_period(db, period)
    start, end = _period_bounds(pay.year, pay.month)
    payload = _active_policy(db)

    b3_raw = payload.get("kpi_manpower_factor")
    param_b3 = D(b3_raw) if b3_raw is not None else D(pay.official_work_days)
    if param_b3 <= 0:
        param_b3 = D(pay.official_work_days) if pay.official_work_days else D(26)
    hours_per_day = D(payload.get("kpi_hours_per_day") or 8)

    employees = db.query(Employee).filter(Employee.deleted_at.is_(None)).all()
    depts = {d.id: d for d in db.query(Department).all()}

    begin_hc = sum(
        1
        for e in employees
        if e.join_date
        and e.join_date < start
        and (e.resign_date is None or e.resign_date >= start)
    )
    # NV không có join_date: tính vào begin nếu đang active
    begin_hc += sum(
        1
        for e in employees
        if e.join_date is None and (e.resign_date is None or e.resign_date >= start)
    )
    recruit = sum(1 for e in employees if e.join_date and start <= e.join_date <= end)
    resign = sum(1 for e in employees if e.resign_date and start <= e.resign_date <= end)
    end_hc = engine.end_headcount(begin_hc, recruit, resign)

    on_period = [e for e in employees if _was_on_payroll(e, start, end)]
    headcount = len(on_period)

    timesheets = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id)
        .all()
    )
    ts_by_emp = {t.employee_id: t for t in timesheets}
    slips = db.query(Payslip).filter(Payslip.pay_period_id == pay.id).all()
    pay_by_emp = {s.employee_id: s for s in slips}

    attendants = ZERO
    ot_hours = ZERO
    ot_pay_total = ZERO
    for e in on_period:
        ts = ts_by_emp.get(e.id)
        if ts:
            attendants += D(ts.worked_days)
            ot_hours += D(ts.ot_hours_weekday) + D(ts.ot_hours_weekend) + D(ts.ot_hours_holiday)
        slip = pay_by_emp.get(e.id)
        if slip:
            ot_pay_total += D(slip.ot_pay)

    manpower = engine.monthly_manpower(headcount, param_b3)
    att_rate = engine.attendance_rate(attendants, manpower)
    ref_h = engine.reference_hours(headcount, D(pay.official_work_days) or param_b3, hours_per_day)
    o_rate = engine.ot_rate(ot_hours, ref_h)
    t_rate = engine.turnover_rate(resign, begin_hc, end_hc)

    # Theo category / bộ phận
    cat_hc: dict[str, int] = {k: 0 for k in CATEGORY_LABELS}
    cat_ot: dict[str, Decimal] = {k: ZERO for k in CATEGORY_LABELS}
    cat_wd: dict[str, Decimal] = {k: ZERO for k in CATEGORY_LABELS}
    dept_rows: dict[str, DeptKpiRow] = {}

    for e in on_period:
        dept = depts.get(e.department_id) if e.department_id else None
        cat = dept.category if dept and dept.category in CATEGORY_LABELS else "direct"
        code = dept.code if dept else "—"
        name = dept.name if dept else "Chưa gán bộ phận"
        ts = ts_by_emp.get(e.id)
        wd = D(ts.worked_days) if ts else ZERO
        ot = (
            D(ts.ot_hours_weekday) + D(ts.ot_hours_weekend) + D(ts.ot_hours_holiday)
            if ts
            else ZERO
        )
        op = D(pay_by_emp[e.id].ot_pay) if e.id in pay_by_emp else ZERO
        cat_hc[cat] = cat_hc.get(cat, 0) + 1
        cat_ot[cat] = cat_ot.get(cat, ZERO) + ot
        cat_wd[cat] = cat_wd.get(cat, ZERO) + wd
        key = code
        if key not in dept_rows:
            dept_rows[key] = DeptKpiRow(
                department_code=code,
                department_name=name,
                category=cat,
                headcount=0,
                worked_days=ZERO,
                ot_hours=ZERO,
                ot_pay=ZERO,
            )
        row = dept_rows[key]
        dept_rows[key] = DeptKpiRow(
            department_code=row.department_code,
            department_name=row.department_name,
            category=row.category,
            headcount=row.headcount + 1,
            worked_days=row.worked_days + wd,
            ot_hours=row.ot_hours + ot,
            ot_pay=row.ot_pay + op,
        )

    open_disputes = (
        db.query(Dispute).filter(Dispute.status.in_(OPEN_STATUSES)).count()
    )

    by_category = [
        ManpowerBucket(
            category=k,
            label=CATEGORY_LABELS[k],
            headcount=cat_hc.get(k, 0),
            ot_hours=cat_ot.get(k, ZERO),
            worked_days=cat_wd.get(k, ZERO),
        )
        for k in ("direct", "prod_indirect", "admin_indirect")
    ]
    by_department = sorted(dept_rows.values(), key=lambda r: (-r.headcount, r.department_code))

    return KpiPeriodOut(
        period=period,
        official_work_days=D(pay.official_work_days),
        salary_divisor=D(pay.salary_divisor),
        param_b3=param_b3,
        hours_per_day=hours_per_day,
        headcount=headcount,
        begin_hc=begin_hc,
        recruit=recruit,
        resign=resign,
        end_hc=end_hc,
        attendants=attendants,
        monthly_manpower=manpower,
        attendance_rate=att_rate,
        attendance_rate_pct=engine.pct(att_rate),
        ot_hours=ot_hours,
        reference_hours=ref_h,
        ot_rate=o_rate,
        ot_rate_pct=engine.pct(o_rate),
        ot_pay_total=engine.money_sum([ot_pay_total]),
        turnover_rate=t_rate,
        turnover_rate_pct=engine.pct(t_rate),
        open_disputes=open_disputes,
        by_category=by_category,
        by_department=by_department,
        formula_note=(
            "attendance = attendants / (HC × B3); "
            "turnover = resign / ((begin+end)/2); "
            "OT rate = ot_hours / (HC × work_days × hours/day). "
            "B3 mặc định = official_work_days (policy kpi_manpower_factor)."
        ),
    )


def overview(db: Session, period: str, *, user: User | None = None) -> OverviewOut:
    kpi = compute_kpi(db, period)
    alerts = (
        db.query(AiAlert)
        .order_by(AiAlert.created_at.desc())
        .limit(8)
        .all()
    )
    total_active = (
        db.query(Employee)
        .filter(Employee.deleted_at.is_(None), Employee.status.in_(["active", "probation"]))
        .count()
    )
    todo_cards: list[TodoCardOut] = []
    if user is not None:
        from app.modules.ai.todos import compute_todo_cards

        todo_cards = compute_todo_cards(db, user).cards
    return OverviewOut(
        period=period,
        total_employees=total_active,
        attendance_rate_pct=kpi.attendance_rate_pct,
        ot_pay_total=kpi.ot_pay_total,
        open_disputes=kpi.open_disputes,
        ot_hours=kpi.ot_hours,
        turnover_rate_pct=kpi.turnover_rate_pct,
        recent_alerts=[
            {
                "id": str(a.id),
                "title": a.title,
                "body": a.body,
                "target_module": a.target_module,
                "is_read": a.is_read,
            }
            for a in alerts
        ],
        by_department=kpi.by_department,
        todo_cards=todo_cards,
    )


def export_kpi_xlsx(db: Session, period: str, *, user_id=None) -> bytes:
    from app.modules.core.export_log import log_export

    kpi = compute_kpi(db, period)
    wb = Workbook()
    ws = wb.active
    ws.title = "KPI"
    ws.append(["Kỳ", kpi.period])
    ws.append(["Headcount", kpi.headcount])
    ws.append(["Begin HC", kpi.begin_hc])
    ws.append(["Recruit", kpi.recruit])
    ws.append(["Resign", kpi.resign])
    ws.append(["End HC", kpi.end_hc])
    ws.append(["Attendants (ngày công)", float(kpi.attendants)])
    ws.append(["B3 (manpower factor)", float(kpi.param_b3)])
    ws.append(["Monthly manpower", float(kpi.monthly_manpower)])
    ws.append(
        [
            "Attendance rate %",
            float(kpi.attendance_rate_pct) if kpi.attendance_rate_pct is not None else None,
        ]
    )
    ws.append(["OT hours", float(kpi.ot_hours)])
    ws.append(["Reference hours", float(kpi.reference_hours)])
    ws.append(
        ["OT rate %", float(kpi.ot_rate_pct) if kpi.ot_rate_pct is not None else None]
    )
    ws.append(
        [
            "Turnover rate %",
            float(kpi.turnover_rate_pct) if kpi.turnover_rate_pct is not None else None,
        ]
    )
    ws.append(["OT pay (VND)", float(kpi.ot_pay_total)])
    ws.append([])
    ws.append(["Bộ phận", "Loại", "HC", "Ngày công", "OT giờ", "OT tiền"])
    for r in kpi.by_department:
        ws.append(
            [
                r.department_name,
                r.category,
                r.headcount,
                float(r.worked_days),
                float(r.ot_hours),
                float(r.ot_pay),
            ]
        )
    buf = BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    if user_id is not None:
        log_export(
            db,
            user_id=user_id,
            kind="kpi",
            period=period,
            row_count=len(kpi.by_department),
            filename=f"kpi_{period}.xlsx",
        )
    return data


def require_report_access(user: User) -> None:
    if not user_can_view_reports(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Trợ Lý AI xin chào {user.full_name}, bạn không có quyền xem Báo cáo/KPI. "
                "Liên hệ Admin."
            ),
        )
