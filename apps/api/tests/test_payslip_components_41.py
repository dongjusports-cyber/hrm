"""4.1 — payslip_components: segment + seq_no, mỗi khoản một dòng."""

from decimal import Decimal
from uuid import UUID

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip, PayslipComponent


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _calculate_5290(client, db):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    pay = ensure_pay_period(db, "2025-10")
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("27")
    ts.al_days = Decimal("0")
    ts.ot_hours_weekday = Decimal("27")
    db.commit()

    from app.modules.payroll import service as payroll_service

    def _rebuild_noop(db_sess, period, *, recalc_days=True):
        ensure_pay_period(db_sess, period)
        return type(
            "R",
            (),
            {"rows_upserted": 1, "message": "noop", "period": period, "pay_period_id": pay.id},
        )()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _rebuild_noop
    try:
        res = client.post("/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client))
    finally:
        payroll_service.rebuild_timesheets = original
    assert res.status_code == 200, res.text
    row = next(p for p in res.json()["payslips"] if p["employee_code"] == "5290")
    return row["id"]


def test_calculate_writes_payslip_components(client, db):
    slip_id = UUID(_calculate_5290(client, db))
    comps = (
        db.query(PayslipComponent)
        .filter(PayslipComponent.payslip_id == slip_id)
        .order_by(PayslipComponent.sort_order.asc())
        .all()
    )
    assert len(comps) >= 5
    codes = {c.component_code for c in comps}
    assert "WD" in codes
    assert "BHXH" in codes
    assert all(c.seq_no >= 1 for c in comps)
    wd = next(c for c in comps if c.component_code == "WD" and c.segment == "official")
    assert wd.amount > 0


def test_components_api(client, db):
    slip_id = _calculate_5290(client, db)
    res = client.get(
        f"/api/payroll/payslips/{slip_id}/components",
        headers=_hr_headers(client),
    )
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) >= 5
    assert items[0]["component_name"]
    assert items[0]["kind"] in ("earning", "deduction", "info")
    wd_rows = [i for i in items if i["component_code"] == "WD"]
    assert len(wd_rows) >= 1
    assert wd_rows[0]["segment"] in ("official", "probation")


def test_two_adjust_lines_different_seq_no(client, db):
    slip_id = UUID(_calculate_5290(client, db))
    slip = db.get(Payslip, slip_id)
    pay = ensure_pay_period(db, "2025-10")
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    from app.modules.payroll.adjustments import create_adjustment, AdjustmentCreate
    from app.modules.core.models import User

    hr = db.query(User).filter(User.username == "hr.demo").one()
    create_adjustment(
        db,
        AdjustmentCreate(
            period="2025-10",
            employee_code="5290",
            kind="addon",
            reason="Truy lĩnh",
            amount=Decimal("100000"),
        ),
        hr,
    )
    create_adjustment(
        db,
        AdjustmentCreate(
            period="2025-10",
            employee_code="5290",
            kind="deduction",
            reason="Trừ đồng phục",
            amount=Decimal("50000"),
        ),
        hr,
    )

    from app.modules.payroll import service as payroll_service

    def _rebuild_noop(db_sess, period, *, recalc_days=True):
        ensure_pay_period(db_sess, period)
        return type("R", (), {"rows_upserted": 1, "message": "noop", "period": period})()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _rebuild_noop
    try:
        client.post("/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client))
    finally:
        payroll_service.rebuild_timesheets = original

    adj_rows = (
        db.query(PayslipComponent)
        .filter(
            PayslipComponent.payslip_id == slip.id,
            PayslipComponent.component_code == "ADJUST",
        )
        .order_by(PayslipComponent.seq_no.asc())
        .all()
    )
    assert len(adj_rows) == 2
    assert adj_rows[0].seq_no == 1
    assert adj_rows[1].seq_no == 2
    assert adj_rows[0].amount > 0
    assert adj_rows[1].amount < 0
