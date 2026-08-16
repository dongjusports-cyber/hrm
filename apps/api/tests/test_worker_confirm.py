"""P4.2 — Worker xác nhận phiếu → khóa."""

from datetime import date, timedelta
from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from tests.worker_auth import unlocked_worker_headers


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _worker_headers(client, code="5290"):
    return unlocked_worker_headers(client, code)


def _calc_and_publish(client, db, code="5290"):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    pay = ensure_pay_period(db, "2025-10")
    emp = db.query(Employee).filter(Employee.employee_code == code).one()
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
        return type(
            "R",
            (),
            {"rows_upserted": 0, "message": "noop", "period": period, "pay_period_id": pay.id},
        )()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _noop
    try:
        assert (
            client.post(
                "/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client)
            ).status_code
            == 200
        )
    finally:
        payroll_service.rebuild_timesheets = original

    pub = client.post("/api/payroll/periods/2025-10/publish", headers=_hr_headers(client))
    assert pub.status_code == 200, pub.text


def test_worker_confirm_locks_payslip(client, db):
    _calc_and_publish(client, db)
    listed = client.get("/api/worker/payslips", headers=_worker_headers(client)).json()
    slip_id = listed[0]["id"]

    res = client.post(
        f"/api/worker/payslips/{slip_id}/confirm",
        headers=_worker_headers(client),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "confirmed"
    assert body["can_confirm"] is False
    assert body["can_dispute"] is False
    assert body["confirmed_at"] is not None

    again = client.post(
        f"/api/worker/payslips/{slip_id}/confirm",
        headers=_worker_headers(client),
    )
    assert again.status_code == 400
    assert "khóa" in again.json()["detail"].lower() or "xác nhận" in again.json()["detail"].lower()

    detail = client.get(
        f"/api/worker/payslips/{slip_id}",
        headers=_worker_headers(client),
    ).json()
    assert detail["status"] == "confirmed"
    assert detail["can_dispute"] is False


def test_other_worker_cannot_confirm(client, db):
    _calc_and_publish(client, db, code="5290")
    slip = (
        db.query(Payslip)
        .join(Employee)
        .filter(Employee.employee_code == "5290", Payslip.status == "published")
        .first()
    )
    assert slip is not None
    res = client.post(
        f"/api/worker/payslips/{slip.id}/confirm",
        headers=_worker_headers(client, "1514"),
    )
    assert res.status_code == 404


def test_expired_payslip_cannot_confirm(client, db):
    _calc_and_publish(client, db)
    slip = (
        db.query(Payslip)
        .join(Employee)
        .filter(Employee.employee_code == "5290", Payslip.status == "published")
        .first()
    )
    assert slip is not None
    slip.confirm_deadline = date.today() - timedelta(days=1)
    db.commit()

    res = client.post(
        f"/api/worker/payslips/{slip.id}/confirm",
        headers=_worker_headers(client),
    )
    assert res.status_code == 400
    assert "hạn" in res.json()["detail"].lower()

    db.refresh(slip)
    assert slip.status == "expired"
