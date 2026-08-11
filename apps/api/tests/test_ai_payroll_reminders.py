"""05§5.3 — nhắc phiếu quá hạn XN + kỳ chưa khóa sau ngày trả lương."""

from datetime import date, timedelta

from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from tests.test_payroll_publish_lock import _prepare_draft


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_payslip_unconfirmed_alert(client, db):
    headers = _prepare_draft(client, db)
    assert client.post("/api/payroll/periods/2025-10/publish", headers=headers).status_code == 200

    slip = db.query(Payslip).join(Employee).filter(Employee.employee_code == "5290").first()
    assert slip is not None
    slip.confirm_deadline = date.today() - timedelta(days=1)
    db.commit()

    alerts = client.get("/api/ai/alerts/mine", headers=_admin_headers(client))
    assert alerts.status_code == 200
    keys = [a["rule_key"] for a in alerts.json()["alerts"]]
    assert "payslip_unconfirmed" in keys


def test_period_lock_overdue_alert(client, db):
    # Kỳ tháng trước rất lâu, còn open → quá hạn ngày 08
    pay = ensure_pay_period(db, "2020-01")
    pay.status = "published"
    db.commit()

    alerts = client.get("/api/ai/alerts/mine", headers=_admin_headers(client))
    assert alerts.status_code == 200
    assert any(
        a["rule_key"] == "period_lock_overdue" and "2020-01" in a["title"]
        for a in alerts.json()["alerts"]
    )
    # idempotent source_ref
    again = client.get("/api/ai/alerts/mine", headers=_admin_headers(client)).json()
    n = sum(1 for a in again["alerts"] if a["rule_key"] == "period_lock_overdue" and "2020-01" in a.get("title", ""))
    assert n == 1
