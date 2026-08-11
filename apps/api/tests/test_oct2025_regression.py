"""
P3.5 — Regression Oct/2025 cho 5 NV neo (08§8.5, 13§13.3).

- Khóa số Hiến pháp/GenuiSuite cho 5290 (nhóm B = 0)
- Idempotent: tính 2 lần → 0đ lệch
- Invariant gross/net cho mọi NV
- Phân loại lệch A/B/C khi có genuisuite_ref
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent, Payslip
from app.modules.payroll.money import D
from app.modules.payroll.regression import classify_money_delta, summarize_classes
from app.modules.payroll.seed_allowances import seed_allowance_types, seed_fixture_allowance_assignments
from app.modules.policy.models import PolicyPackage

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "oct2025_5nv.json"

# Oct/2025 neo GenusSuite — mức chuyên cần/đi lại tháng đó (khác default 22.12 sau 2.6).
_OCT2025_POLICY_MONEY = {
    "attendance_bonus_monthly": 230_000,
    "transport_monthly_default": 760_000,
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upsert_assignment(db, emp: Employee, code: str, amount: Decimal | None) -> None:
    seed_allowance_types(db)
    at = db.query(PayComponent).filter(PayComponent.code == code).one()
    row = (
        db.query(EmployeeAllowanceAssignment)
        .filter(
            EmployeeAllowanceAssignment.employee_id == emp.id,
            EmployeeAllowanceAssignment.allowance_type_id == at.id,
        )
        .one_or_none()
    )
    if row is None:
        db.add(
            EmployeeAllowanceAssignment(
                employee_id=emp.id,
                allowance_type_id=at.id,
                amount=amount,
            )
        )
    else:
        row.amount = amount


def _clear_toxic(db, emp: Employee) -> None:
    at = db.query(PayComponent).filter(PayComponent.code == "TOXIC").one_or_none()
    if at is None:
        return
    db.query(EmployeeAllowanceAssignment).filter(
        EmployeeAllowanceAssignment.employee_id == emp.id,
        EmployeeAllowanceAssignment.allowance_type_id == at.id,
    ).delete()


def apply_oct2025_fixture(db) -> dict:
    data = _load_fixture()
    period = data["period"]
    pkg = db.query(PolicyPackage).order_by(PolicyPackage.id).first()
    if pkg and isinstance(pkg.payload, dict):
        payload = dict(pkg.payload)
        payload.update(_OCT2025_POLICY_MONEY)
        pkg.payload = payload
        db.commit()
    seed_fixture_allowance_assignments(db)
    ensure_pay_period(db, period)
    rebuild_timesheets(db, period, recalc_days=False)
    pay = ensure_pay_period(db, period)

    for emp_fx in data["employees"]:
        code = emp_fx["employee_code"]
        emp = db.query(Employee).filter(Employee.employee_code == code).one()
        ts = (
            db.query(TimesheetMonth)
            .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
            .one()
        )
        t = emp_fx["timesheet"]
        ts.worked_days = D(t["worked_days"])
        ts.al_days = D(t["al_days"])
        ts.rem_days = D(t["rem_days"])
        ts.late_count = int(t["late_count"])
        ts.early_count = int(t["early_count"])
        ts.ot_hours_weekday = D(t["ot_hours_weekday"])
        ts.ot_hours_weekend = D(t["ot_hours_weekend"])
        ts.ot_hours_holiday = D(t["ot_hours_holiday"])

        if emp_fx.get("no_toxic"):
            _clear_toxic(db, emp)
        for acode, amt in (emp_fx.get("allowance_overrides") or {}).items():
            _upsert_assignment(db, emp, acode, D(amt))

    db.commit()
    return data


def calculate_keep_timesheet(client, db, period: str):
    """Tính lương nhưng không rebuild timesheet từ punch (giữ fixture công)."""
    from app.modules.attendance.timesheet import ensure_pay_period as ensure
    from app.modules.payroll import service as payroll_service

    pay = ensure(db, period)

    def _noop(db_sess, p, *, recalc_days=True):
        ensure(db_sess, p)
        return type(
            "R",
            (),
            {"rows_upserted": 0, "message": "noop", "period": p, "pay_period_id": pay.id},
        )()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _noop
    try:
        return client.post(
            f"/api/payroll/periods/{period}/calculate",
            headers=_hr_headers(client),
        )
    finally:
        payroll_service.rebuild_timesheets = original


def _by_code(payslips: list[dict]) -> dict[str, dict]:
    return {p["employee_code"]: p for p in payslips}


def test_oct2025_five_employees_invariants_and_neo(client, db):
    data = apply_oct2025_fixture(db)
    period = data["period"]
    res = calculate_keep_timesheet(client, db, period)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["run"]["status"] == "success"
    by = _by_code(body["payslips"])

    # Đủ 5 NV neo
    for emp_fx in data["employees"]:
        assert emp_fx["employee_code"] in by

    # Neo 5290 — khóa Hiến pháp / GenuiSuite logic
    p5290 = by["5290"]
    assert D(p5290["wd_salary"]) == Decimal("5893269")
    assert D(p5290["ot_pay"]) == Decimal("1276334")
    assert D(p5290["bhxh"]) == Decimal("506000")
    assert D(p5290["bhyt"]) == Decimal("94875")
    assert D(p5290["bhtn"]) == Decimal("63250")
    assert D(p5290["union_fee"]) == Decimal("44100")
    assert D(p5290["lines"]["si_contribution_base"]) == Decimal("6325000")
    assert D(p5290["lines"]["ot"]["ot_base"]) == Decimal("6555000")

    comparisons: list[dict] = []
    for emp_fx in data["employees"]:
        code = emp_fx["employee_code"]
        slip = by[code]
        # Invariant nội bộ
        gross = D(slip["wd_salary"]) + D(slip["allowance_total"]) + D(slip["ot_pay"]) + D(
            slip.get("other_adjustments") or 0
        )
        assert D(slip["gross"]) == gross
        net = (
            D(slip["gross"])
            - D(slip["bhxh"])
            - D(slip["bhyt"])
            - D(slip["bhtn"])
            - D(slip["union_fee"])
            - D(slip.get("other_deductions") or 0)
        )
        assert D(slip["net"]) == net

        ref = emp_fx.get("genuisuite_ref") or {}
        exc = set(emp_fx.get("exception_c_fields") or [])
        for field, gs in ref.items():
            if field == "si_contribution_base":
                dj_val = D(slip["lines"]["si_contribution_base"])
            else:
                dj_val = D(slip[field])
            comparisons.append(
                classify_money_delta(
                    dj_val,
                    D(gs),
                    field=f"{code}.{field}",
                    marked_exception_c=field in exc,
                )
            )

    summary = summarize_classes(comparisons)
    assert summary["B"] == 0, comparisons
    # 5290 refs phải OK (hoặc A ≤ 50đ)
    for c in comparisons:
        if c["field"].startswith("5290."):
            assert c["class"] in ("OK", "A"), c


def test_oct2025_idempotent_recalculate(client, db):
    data = apply_oct2025_fixture(db)
    period = data["period"]
    r1 = calculate_keep_timesheet(client, db, period)
    assert r1.status_code == 200
    first = {p["employee_code"]: p for p in r1.json()["payslips"]}

    r2 = calculate_keep_timesheet(client, db, period)
    assert r2.status_code == 200
    second = {p["employee_code"]: p for p in r2.json()["payslips"]}

    money_fields = (
        "wd_salary",
        "allowance_total",
        "ot_pay",
        "gross",
        "bhxh",
        "bhyt",
        "bhtn",
        "union_fee",
        "net",
    )
    for code in first:
        for f in money_fields:
            assert D(first[code][f]) == D(second[code][f]), f"{code}.{f} lệch khi tính lại"


def test_classify_delta_helpers():
    assert classify_money_delta(Decimal("100"), Decimal("100"), field="x")["class"] == "OK"
    assert classify_money_delta(Decimal("100"), Decimal("90"), field="x")["class"] == "A"
    assert classify_money_delta(Decimal("100"), Decimal("0"), field="x")["class"] == "B"
    assert (
        classify_money_delta(Decimal("100"), Decimal("0"), field="x", marked_exception_c=True)["class"]
        == "C"
    )


def test_fixture_file_lists_five_anchor_codes():
    data = _load_fixture()
    codes = {e["employee_code"] for e in data["employees"]}
    assert codes == {"1514", "1643", "5290", "5321", "1732"}
    assert data["salary_divisor"] == "26"
