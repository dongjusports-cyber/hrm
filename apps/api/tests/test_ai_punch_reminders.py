"""Luật 01 — AI cảnh báo chấm lẻ (thiếu vào hoặc ra)."""

from datetime import datetime

from app.core.config import get_settings
from app.modules.attendance.engine import VN_TZ
from app.modules.mdm.models import Employee
from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


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


def _ingest_odd_punch_today(client):
    today = datetime.now(tz=VN_TZ).date()
    iso = today.isoformat()
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": f"{iso}T08:00:00+07:00"},
            ]
        },
    )
    assert res.status_code == 200, res.text
    return today


def test_punch_odd_todo_and_alert(client):
    _ingest_odd_punch_today(client)
    headers = _hr_headers(client)

    todos = client.get("/api/ai/todos", headers=headers)
    assert todos.status_code == 200, todos.text
    cards = todos.json()["cards"]
    punch = next(c for c in cards if c["key"] == "punch_odd_current")
    assert punch["count"] >= 1
    assert punch["href"] == "/m/timekeeping?view=daily"
    assert "biên bản" in punch["body"]

    alerts = client.get("/api/ai/alerts/mine", headers=headers)
    assert alerts.status_code == 200
    odd = [a for a in alerts.json()["alerts"] if a["rule_key"] == "punch_odd"]
    assert len(odd) >= 1
    assert "không tự bịa" in odd[0]["body"].lower() or "không tự bịa" in odd[0]["title"].lower() or "chấm lẻ" in odd[0]["title"]

    again = client.get("/api/ai/alerts/mine", headers=headers).json()
    n = sum(1 for a in again["alerts"] if a["rule_key"] == "punch_odd")
    assert n == 1


def test_ai_query_punch_review_direct(client):
    _ingest_odd_punch_today(client)
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Ai chấm lẻ tháng này"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "punch_review"
    assert body["stub"] is False
    assert body["model_name"] == "direct"
    assert "5290" in body["answer"]
    assert "Kết quả rà soát chấm lẻ" in body["answer"]


def test_ai_query_employee_lookup_includes_leave_and_punch(client):
    _ingest_odd_punch_today(client)
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Thông tin MSNV 5290"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "employee_lookup"
    assert "Phép năm" in body["answer"]
    assert "Chấm lẻ" in body["answer"]


def test_attendance_penalty_risk_todo(client, db):
    today = datetime.now(tz=VN_TZ).date()
    period = f"{today.year:04d}-{today.month:02d}"
    pay = ensure_pay_period(db, period)
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one_or_none()
    )
    if ts is None:
        ts = TimesheetMonth(pay_period_id=pay.id, employee_id=emp.id)
        db.add(ts)
        db.flush()
    ts.late_count = 2
    db.commit()

    res = client.get("/api/ai/todos", headers=_hr_headers(client))
    assert res.status_code == 200
    keys = {c["key"] for c in res.json()["cards"]}
    assert "attendance_penalty_risk" in keys
