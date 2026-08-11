"""P2.1 — Mitapro punch ingest + sync_jobs."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_push_requires_agent_token(client):
    res = client.post(
        "/api/integrations/mitapro/push",
        json={"punches": []},
    )
    assert res.status_code == 401


def test_push_punches_idempotent(client):
    payload = {
        "punches": [
            {
                "employee_code": "5290",
                "punch_time": "2025-10-01T08:01:00+07:00",
                "ma_cham_cong": "FP001",
            },
            {
                "employee_code": "5290",
                "punch_time": "2025-10-01T17:05:00+07:00",
                "ma_cham_cong": "FP001",
            },
        ],
        "agent_name": "test-agent",
    }
    res1 = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json=payload,
    )
    assert res1.status_code == 200, res1.text
    assert res1.json()["job"]["records_inserted"] == 2
    assert res1.json()["job"]["status"] == "success"

    res2 = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json=payload,
    )
    assert res2.status_code == 200
    assert res2.json()["job"]["records_inserted"] == 0
    assert res2.json()["job"]["records_skipped"] == 2


def test_push_unknown_msnv_partial(client):
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {
                    "employee_code": "9999",
                    "punch_time": "2025-10-02T08:00:00+07:00",
                }
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["job"]["status"] == "partial"
    assert "9999" in res.json()["job"]["message"]


def test_sync_now_and_status(client):
    headers = _hr_headers(client)
    sync = client.post("/api/attendance/sync-now", headers=headers)
    assert sync.status_code == 200
    assert sync.json()["status"] == "requested"

    status = client.get("/api/integrations/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["last_job"]["status"] == "requested"
    assert body["punch_count"] >= 0
