"""Agent push nhiều chunk — job giữ running đến chunk cuối."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_push_multi_chunk_same_job(client):
    job = client.post("/api/attendance/sync-now", headers=_hr_headers(client)).json()
    job_id = job["id"]

    client.post(
        f"/api/integrations/mitapro/pending/{job_id}/claim",
        headers=_agent_headers(),
    )

    res1 = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "claimed_job_id": job_id,
            "chunk_final": False,
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-10T08:00:00+07:00"},
            ],
        },
    )
    assert res1.status_code == 200, res1.text
    mid = res1.json()["job"]
    assert mid["id"] == job_id
    assert mid["status"] == "running"
    assert mid["records_in"] == 1

    res2 = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "claimed_job_id": job_id,
            "chunk_final": True,
            "synced_from": "2025-10-10T00:00:00+07:00",
            "synced_to": "2025-10-10T23:59:59+07:00",
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-10T17:00:00+07:00"},
            ],
        },
    )
    assert res2.status_code == 200, res2.text
    final = res2.json()["job"]
    assert final["id"] == job_id
    assert final["records_in"] == 2
    assert final["status"] in ("success", "partial", "running")
