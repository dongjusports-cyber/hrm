"""P3.6 — publish / lock kỳ lương."""

from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _prepare_draft(client, db):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    pay = ensure_pay_period(db, "2025-10")
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("27")
    db.commit()

    from app.modules.attendance.timesheet import ensure_pay_period as ensure
    from app.modules.payroll import service as payroll_service

    def _noop(db_sess, period, *, recalc_days=True):
        ensure(db_sess, period)
        return type("R", (), {"rows_upserted": 0, "message": "noop", "period": period, "pay_period_id": pay.id})()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _noop
    try:
        res = client.post("/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client))
    finally:
        payroll_service.rebuild_timesheets = original
    assert res.status_code == 200, res.text
    return _hr_headers(client)


def test_publish_then_lock_flow(client, db):
    headers = _prepare_draft(client, db)

    meta = client.get("/api/payroll/periods/2025-10", headers=headers)
    assert meta.status_code == 200
    assert meta.json()["status"] == "calculating"

    pub = client.post("/api/payroll/periods/2025-10/publish", headers=headers)
    assert pub.status_code == 200, pub.text
    assert pub.json()["period"]["status"] == "published"
    assert pub.json()["affected_payslips"] >= 1

    slip = db.query(Payslip).join(Employee).filter(Employee.employee_code == "5290").first()
    assert slip is not None
    assert slip.status == "published"
    assert slip.confirm_deadline is not None

    # Không tính lại sau publish
    blocked = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert blocked.status_code == 400

    lock = client.post("/api/payroll/periods/2025-10/lock", headers=headers)
    assert lock.status_code == 200
    assert lock.json()["period"]["status"] == "locked"

    # Không publish khi đã khóa
    again = client.post("/api/payroll/periods/2025-10/publish", headers=headers)
    assert again.status_code == 400

    # HR không được mở khóa
    hr_unlock = client.post("/api/payroll/periods/2025-10/unlock", headers=headers)
    assert hr_unlock.status_code == 403

    admin_tok = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    admin_h = {"Authorization": f"Bearer {admin_tok}"}
    unlocked = client.post("/api/payroll/periods/2025-10/unlock", headers=admin_h)
    assert unlocked.status_code == 200, unlocked.text
    assert unlocked.json()["period"]["status"] == "published"

    # HR không reopen
    assert client.post("/api/payroll/periods/2025-10/reopen", headers=headers).status_code == 403

    reopened = client.post("/api/payroll/periods/2025-10/reopen", headers=admin_h)
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["period"]["status"] == "calculating"
    slip = db.query(Payslip).join(Employee).filter(Employee.employee_code == "5290").first()
    assert slip is not None
    assert slip.status == "draft"

    # Tính lại được sau reopen
    calc2 = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert calc2.status_code == 200, calc2.text


def test_lock_requires_publish(client, db):
    headers = _prepare_draft(client, db)
    res = client.post("/api/payroll/periods/2025-10/lock", headers=headers)
    assert res.status_code == 400


def test_get_payslip_detail(client, db):
    headers = _prepare_draft(client, db)
    listed = client.get("/api/payroll/payslips", headers=headers, params={"period": "2025-10"}).json()
    pid = listed[0]["id"]
    detail = client.get(f"/api/payroll/payslips/{pid}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == pid
    assert "net" in detail.json()
