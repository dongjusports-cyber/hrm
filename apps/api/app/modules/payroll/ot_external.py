"""
OT ngoài — tính tiền theo 22§22.8 (cùng ot_base, làm tròn 30p) nhưng KHÔNG vào payslip/BHXH/PIT.

Chi trả kênh ATM riêng (policy ot_split.exclude_from_payslip).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.core.export_log import log_export
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.payroll.engine_allowances import AllowanceInput, compute_allowances, should_zero_probation_allowances
from app.modules.payroll.engine_ot import OtHours, OtInput, compute_ot_pay
from app.modules.payroll.money import D, ZERO, money_vnd
from app.modules.payroll.period_eligibility import employee_on_payroll_period
from app.modules.payroll.service import (
    _active_policy,
    _detail_days_by_category,
    _leave_days_by_code,
    _monthly_map,
    _penalty_summary_for_employee,
    _type_views,
)


@dataclass(frozen=True)
class OtExternalPayRow:
    employee_code: str
    full_name: str
    bank_account: str
    raw_hours: Decimal
    effective_hours: Decimal
    ot_base: Decimal
    hourly_base: Decimal
    rate: Decimal
    amount_vnd: Decimal


@dataclass(frozen=True)
class OtExternalSummary:
    period: str
    employee_count: int
    total_raw_hours: Decimal
    total_effective_hours: Decimal
    total_amount_vnd: Decimal
    rows: list[OtExternalPayRow]
    policy_note: str


def _external_rate(policy: dict) -> Decimal:
    ot_split = policy.get("ot_split") or {}
    ext = ot_split.get("ot_external") or {}
    rate_key = str(ext.get("rate_key", "weekday")).strip().lower()
    rates = policy.get("ot_rates") or {}
    return D(rates.get(rate_key, rates.get("weekday", "1.5")))


def split_external_ot_hours(
    *,
    external: Decimal,
    weekend: Decimal = ZERO,
    holiday: Decimal = ZERO,
) -> OtHours:
    """Tách giờ OT ngoài để tính tiền (ngày thường 1,5 · CN 2,0 · lễ 2–3).

    Sau rebuild: `external` = weekday_ext + CN + lễ.
    Dữ liệu cũ: `external` chỉ weekday_ext — nếu trừ CN/lễ ra âm thì giữ nguyên external.
    """
    ext = D(external)
    we = D(weekend)
    ho = D(holiday)
    wd = ext - we - ho
    if wd < 0:
        wd = ext
    return OtHours(weekday=wd, weekend=we, holiday=ho)


def _display_rate(hours: OtHours, policy: dict) -> Decimal:
    rates = policy.get("ot_rates") or {}
    pairs = [
        (hours.weekday, D(rates.get("weekday", "1.5"))),
        (hours.weekend, D(rates.get("weekend", rates.get("sunday", "2.0")))),
        (hours.holiday, D(rates.get("holiday", "2.0"))),
    ]
    best = max(pairs, key=lambda p: p[0])
    if best[0] <= 0:
        return _external_rate(policy)
    return best[1]


def compute_ot_external_row(
    db: Session,
    pay: PayPeriod,
    emp: Employee,
    ts: TimesheetMonth,
    payload: dict,
) -> OtExternalPayRow | None:
    hours = split_external_ot_hours(
        external=D(ts.ot_hours_external),
        weekend=D(ts.ot_hours_weekend),
        holiday=D(ts.ot_hours_holiday),
    )
    raw = hours.weekday + hours.weekend + hours.holiday
    if raw <= 0:
        return None

    type_views = _type_views(db)
    monthly = _monthly_map(db, emp.id)
    penalty_sum = _penalty_summary_for_employee(db, pay, emp, payload)
    leave_days = _leave_days_by_code(db, pay.id, emp.id, ts.id)
    detail_days = _detail_days_by_category(db, ts.id)

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
            hours=hours,
            policy=payload,
        )
    )
    eff_map = ot_res.detail.get("effective_hours") or {}
    eff = D(eff_map.get("weekday", "0")) + D(eff_map.get("weekend", "0")) + D(eff_map.get("holiday", "0"))
    if eff <= 0 and ot_res.ot_pay <= 0:
        return OtExternalPayRow(
            employee_code=emp.employee_code,
            full_name=emp.full_name,
            bank_account=emp.bank_account or "",
            raw_hours=raw,
            effective_hours=ZERO,
            ot_base=ZERO,
            hourly_base=ZERO,
            rate=_display_rate(hours, payload),
            amount_vnd=ZERO,
        )
    return OtExternalPayRow(
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        bank_account=emp.bank_account or "",
        raw_hours=raw,
        effective_hours=eff,
        ot_base=ot_res.ot_base,
        hourly_base=ot_res.ot_hourly_base,
        rate=_display_rate(hours, payload),
        amount_vnd=ot_res.ot_pay,
    )


def build_ot_external_summary(db: Session, period: str) -> OtExternalSummary:
    pay = ensure_pay_period(db, period)
    _, payload = _active_policy(db)
    ot_split = payload.get("ot_split") or {}
    ext_cfg = ot_split.get("ot_external") or {}
    note = str(
        ext_cfg.get(
            "note",
            "OT ngoài: ngày thường 1,5 · CN 2,0 · lễ 2–3 — không vào payslip/BHXH/PIT, chi ATM riêng.",
        )
    )

    q = (
        db.query(TimesheetMonth, Employee)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(
            TimesheetMonth.pay_period_id == pay.id,
            or_(
                TimesheetMonth.ot_hours_external > 0,
                TimesheetMonth.ot_hours_weekend > 0,
                TimesheetMonth.ot_hours_holiday > 0,
            ),
            Employee.deleted_at.is_(None),
        )
        .order_by(Employee.employee_code.asc())
    )

    rows: list[OtExternalPayRow] = []
    for ts_row, emp in q.all():
        if not employee_on_payroll_period(emp, pay.date_from, pay.date_to):
            continue
        row = compute_ot_external_row(db, pay, emp, ts_row, payload)
        if row is not None:
            rows.append(row)

    total_raw = sum((r.raw_hours for r in rows), ZERO)
    total_eff = sum((r.effective_hours for r in rows), ZERO)
    total_amt = sum((r.amount_vnd for r in rows), ZERO)

    return OtExternalSummary(
        period=period,
        employee_count=len(rows),
        total_raw_hours=total_raw,
        total_effective_hours=total_eff,
        total_amount_vnd=money_vnd(total_amt),
        rows=rows,
        policy_note=note,
    )


def build_ot_external_excel(summary: OtExternalSummary) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "OT_NGOAI"
    bold = Font(bold=True)

    ws.append(["Bảng OT ngoài — chi ATM riêng (không vào audit lương chính)"])
    ws.append([f"Kỳ: {summary.period}", summary.policy_note])
    ws.append([])

    headers = [
        "STT",
        "MSNV",
        "Họ tên",
        "Giờ thô",
        "Giờ tính (30p)",
        "Nền OT",
        "Đơn giá/h",
        "Hệ số",
        "Tiền OT (VND)",
        "Số TK",
        "Ghi chú",
    ]
    ws.append(headers)
    header_row = ws.max_row
    for c in range(1, len(headers) + 1):
        ws.cell(row=header_row, column=c).font = bold

    for i, r in enumerate(summary.rows, start=1):
        ws.append(
            [
                i,
                r.employee_code,
                r.full_name,
                float(r.raw_hours),
                float(r.effective_hours),
                int(r.ot_base),
                int(r.hourly_base),
                float(r.rate),
                int(r.amount_vnd),
                r.bank_account,
                f"OT ngoài {summary.period}",
            ]
        )

    ws.append([])
    ws.append(
        [
            "",
            "Tổng NV",
            summary.employee_count,
            float(summary.total_raw_hours),
            float(summary.total_effective_hours),
            "",
            "",
            "",
            int(summary.total_amount_vnd),
        ]
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_ot_external(db: Session, period: str, actor: User) -> tuple[bytes, str]:
    summary = build_ot_external_summary(db, period)
    data = build_ot_external_excel(summary)
    filename = f"OT_ngoai_{period}.xlsx"
    log_export(
        db,
        user_id=actor.id,
        kind="ot_external",
        period=period,
        row_count=summary.employee_count,
        filename=filename,
    )
    db.commit()
    return data, filename
