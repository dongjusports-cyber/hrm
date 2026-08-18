"""P2.3 — API recalculate + list attendance days."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_push_auto_builds_attendance_day(client):
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:01:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-01T17:05:00+07:00"},
            ]
        },
    )
    assert res.status_code == 200

    days = client.get(
        "/api/attendance/days",
        headers=_hr_headers(client),
        params={"from": "2025-10-01", "to": "2025-10-01", "employee_code": "5290"},
    )
    assert days.status_code == 200, days.text
    body = days.json()
    assert len(body) == 1
    assert body[0]["late_minutes"] == 1
    assert body[0]["ot_minutes"] == 0  # 17:05 nghỉ cơm — không OT
    assert body[0]["ot_on_books_minutes"] == 0
    assert body[0]["ot_external_minutes"] == 0
    assert body[0]["ot_type"] is None
    assert body[0]["punch_count"] == 2


def test_recalculate_endpoint(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "1514", "punch_time": "2025-10-02T08:00:00+07:00"},
                {"employee_code": "1514", "punch_time": "2025-10-02T16:30:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    recalc = client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-02", "to": "2025-10-02", "employee_code": "1514"},
    )
    assert recalc.status_code == 200
    assert recalc.json()["days_upserted"] == 1

    days = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-02", "to": "2025-10-02"},
    ).json()
    assert days[0]["early_minutes"] == 30
    assert days[0]["late_minutes"] == 0
