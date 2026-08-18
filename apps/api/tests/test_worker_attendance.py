"""GET /api/worker/attendance — công nhân xem công của chính mình, không ghi DB."""

from sqlalchemy import event

from app.core.config import get_settings
from tests.worker_auth import unlocked_worker_headers


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def test_worker_sees_own_attendance_day(client):
    pushed = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:01:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-01T17:05:00+07:00"},
            ]
        },
    )
    assert pushed.status_code == 200, pushed.text

    res = client.get(
        "/api/worker/attendance",
        headers=unlocked_worker_headers(client, "5290"),
        params={"period": "2025-10"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period"] == "2025-10"
    oct1 = next((d for d in body["days"] if d["work_date"] == "2025-10-01"), None)
    assert oct1 is not None
    assert oct1["first_in"]
    assert oct1["last_out"]
    assert oct1["late_minutes"] == 1


def test_worker_attendance_only_own_code(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "1514", "punch_time": "2025-10-02T08:00:00+07:00"},
                {"employee_code": "1514", "punch_time": "2025-10-02T17:00:00+07:00"},
            ]
        },
    )
    res = client.get(
        "/api/worker/attendance",
        headers=unlocked_worker_headers(client, "5290"),
        params={"period": "2025-10"},
    )
    assert res.status_code == 200, res.text
    days = res.json()["days"]
    assert not any(d["work_date"] == "2025-10-02" and d["first_in"] for d in days)


def test_staff_cannot_read_worker_attendance(client):
    token = client.post(
        "/api/auth/login",
        json={"username": "hr.demo", "password": "HrDemo@123456"},
    ).json()["access_token"]
    res = client.get("/api/worker/attendance", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_worker_attendance_get_is_readonly(client, db):
    headers = unlocked_worker_headers(client, "1514")
    warm = client.get("/api/worker/attendance", headers=headers, params={"period": "2025-10"})
    assert warm.status_code == 200, warm.text

    statements: list[str] = []

    def _record(conn, cursor, statement, params, context, executemany) -> None:
        statements.append(statement.strip().split(maxsplit=1)[0].upper())

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", _record)
    try:
        res = client.get("/api/worker/attendance", headers=headers, params={"period": "2025-10"})
    finally:
        event.remove(bind, "before_cursor_execute", _record)

    assert res.status_code == 200, res.text
    writes = [s for s in statements if s in ("INSERT", "UPDATE", "DELETE")]
    assert writes == [], f"GET /worker/attendance ghi DB: {writes} / {statements}"
