"""P2.5 — AI Lớp A: alert khi Agent sync lỗi / partial."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_partial_sync_creates_admin_alert(client):
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "9999", "punch_time": "2025-10-03T08:00:00+07:00"},
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["job"]["status"] == "partial"

    mine = client.get("/api/ai/alerts/mine", headers=_admin_headers(client))
    assert mine.status_code == 200
    body = mine.json()
    assert body["unread_count"] >= 1
    assert any(a["rule_key"] == "sync_partial" for a in body["alerts"])


def test_hr_user_does_not_see_sync_alerts(client):
    client.post(
        "/api/integrations/mitapro/error",
        headers=_agent_headers(),
        json={"message": "Không kết nối được SQL Mitapro", "agent_name": "test"},
    )
    hr = client.get("/api/ai/alerts/mine", headers=_hr_headers(client))
    assert hr.status_code == 200
    assert all(not a["rule_key"].startswith("sync_") for a in hr.json()["alerts"])


def test_agent_error_and_mark_read(client):
    err = client.post(
        "/api/integrations/mitapro/error",
        headers=_agent_headers(),
        json={"message": "ODBC timeout", "agent_name": "factory-pc"},
    )
    assert err.status_code == 200
    assert err.json()["status"] == "error"

    admin = _admin_headers(client)
    mine = client.get("/api/ai/alerts/mine", headers=admin).json()
    alert = next(a for a in mine["alerts"] if a["rule_key"] == "sync_error")
    assert "ODBC" in alert["body"]

    read = client.post(f"/api/ai/alerts/{alert['id']}/read", headers=admin)
    assert read.status_code == 200
    assert read.json()["is_read"] is True

    mine2 = client.get("/api/ai/alerts/mine", headers=admin, params={"unread_only": True}).json()
    assert all(a["id"] != alert["id"] for a in mine2["alerts"])


def test_sync_error_streak_alert(client):
    for i in range(3):
        client.post(
            "/api/integrations/mitapro/error",
            headers=_agent_headers(),
            json={"message": f"lỗi lần {i+1}", "agent_name": "pc"},
        )
    mine = client.get("/api/ai/alerts/mine", headers=_admin_headers(client)).json()
    assert any(a["rule_key"] == "sync_error_streak" for a in mine["alerts"])
