"""P4.3 — Worker khiếu nại → ticket + badge AI."""

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


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
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


def test_worker_dispute_creates_ticket_and_alert(client, db):
    _calc_and_publish(client, db)
    listed = client.get("/api/worker/payslips", headers=_worker_headers(client)).json()
    slip_id = listed[0]["id"]

    reasons = client.get("/api/worker/dispute-reasons", headers=_worker_headers(client))
    assert reasons.status_code == 200
    assert any(r["code"] == "wrong_ot" for r in reasons.json())

    res = client.post(
        f"/api/worker/payslips/{slip_id}/dispute",
        headers=_worker_headers(client),
        json={"reason_code": "wrong_ot", "description": "OT cuối tuần thiếu 4 giờ."},
    )
    assert res.status_code == 200, res.text
    ticket = res.json()
    assert ticket["code"].startswith("K")
    assert ticket["status"] == "open"
    assert ticket["reason_code"] == "wrong_ot"
    assert ticket["employee_code"] == "5290"

    detail = client.get(
        f"/api/worker/payslips/{slip_id}",
        headers=_worker_headers(client),
    ).json()
    assert detail["status"] == "disputed"
    assert detail["can_confirm"] is False
    assert detail["can_dispute"] is False

    # Không gửi lần 2
    again = client.post(
        f"/api/worker/payslips/{slip_id}/dispute",
        headers=_worker_headers(client),
        json={"reason_code": "other", "description": "Gửi lại."},
    )
    assert again.status_code == 400

    # HR thấy ticket + badge
    disputes = client.get("/api/disputes", headers=_hr_headers(client))
    assert disputes.status_code == 200
    assert any(d["code"] == ticket["code"] for d in disputes.json())

    alerts = client.get("/api/ai/alerts/mine", headers=_hr_headers(client)).json()
    assert alerts["unread_count"] >= 1
    assert any(a["rule_key"] == "dispute_new" for a in alerts["alerts"])


def test_confirmed_payslip_cannot_dispute(client, db):
    _calc_and_publish(client, db)
    listed = client.get("/api/worker/payslips", headers=_worker_headers(client)).json()
    slip_id = listed[0]["id"]
    assert (
        client.post(
            f"/api/worker/payslips/{slip_id}/confirm",
            headers=_worker_headers(client),
        ).status_code
        == 200
    )
    res = client.post(
        f"/api/worker/payslips/{slip_id}/dispute",
        headers=_worker_headers(client),
        json={"reason_code": "wrong_net", "description": "Thử khiếu nại sau khóa."},
    )
    assert res.status_code == 400
    assert "khóa" in res.json()["detail"].lower() or "xác nhận" in res.json()["detail"].lower()


def test_other_worker_cannot_dispute(client, db):
    _calc_and_publish(client, db, code="5290")
    slip = (
        db.query(Payslip)
        .join(Employee)
        .filter(Employee.employee_code == "5290", Payslip.status == "published")
        .first()
    )
    assert slip is not None
    res = client.post(
        f"/api/worker/payslips/{slip.id}/dispute",
        headers=_worker_headers(client, "1514"),
        json={"reason_code": "other", "description": "Không phải phiếu của tôi."},
    )
    assert res.status_code == 404
