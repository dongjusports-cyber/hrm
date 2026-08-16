"""P4.4 — Inbox khiếu nại: assign + đóng → payslip resolved."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.dispute.models import Dispute
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

    assert (
        client.post("/api/payroll/periods/2025-10/publish", headers=_hr_headers(client)).status_code
        == 200
    )


def _open_dispute(client, db) -> str:
    _calc_and_publish(client, db)
    slip_id = client.get("/api/worker/payslips", headers=_worker_headers(client)).json()[0]["id"]
    res = client.post(
        f"/api/worker/payslips/{slip_id}/dispute",
        headers=_worker_headers(client),
        json={"reason_code": "wrong_days", "description": "Thiếu 1 ngày công."},
    )
    assert res.status_code == 200, res.text
    return res.json()["id"]


def test_assign_and_close_dispute(client, db):
    dispute_id = _open_dispute(client, db)

    assigned = client.post(
        f"/api/disputes/{dispute_id}/assign",
        headers=_hr_headers(client),
        json={},
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["status"] == "hr_pending"
    assert body["assigned_user_name"]
    assert body["payslip_status"] == "disputed"

    closed = client.post(
        f"/api/disputes/{dispute_id}/close",
        headers=_hr_headers(client),
        json={"note": "Đã đối chiếu punch — giữ nguyên phiếu."},
    )
    assert closed.status_code == 200, closed.text
    c = closed.json()
    assert c["status"] == "closed"
    assert c["payslip_status"] == "resolved"
    assert c["hr_note"] and "đối chiếu" in c["hr_note"].lower()
    assert c["closed_at"] is not None

    slip = db.query(Payslip).filter(Payslip.id == UUID(c["payslip_id"])).one()
    assert slip.status == "resolved"

    # Republish resolved slip
    pub = client.post("/api/payroll/periods/2025-10/publish", headers=_hr_headers(client))
    assert pub.status_code == 200, pub.text
    db.refresh(slip)
    assert slip.status == "published"

    again = client.post(
        f"/api/disputes/{dispute_id}/close",
        headers=_hr_headers(client),
        json={},
    )
    assert again.status_code == 400


def test_filter_open_disputes(client, db):
    dispute_id = _open_dispute(client, db)
    open_list = client.get("/api/disputes?status=open", headers=_hr_headers(client)).json()
    assert any(d["id"] == dispute_id for d in open_list)

    client.post(
        f"/api/disputes/{dispute_id}/close",
        headers=_hr_headers(client),
        json={"note": "Đóng."},
    )
    open_after = client.get("/api/disputes?status=open", headers=_hr_headers(client)).json()
    assert not any(d["id"] == dispute_id for d in open_after)


def test_stale_dispute_alert(client, db):
    dispute_id = _open_dispute(client, db)
    row = db.get(Dispute, UUID(dispute_id))
    assert row is not None
    row.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()

    client.get("/api/disputes", headers=_hr_headers(client))
    alerts = client.get("/api/ai/alerts/mine", headers=_hr_headers(client)).json()
    assert any(a["rule_key"] == "dispute_stale" for a in alerts["alerts"])
