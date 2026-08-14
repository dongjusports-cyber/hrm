"""Test claimed_job_id — ingest cập nhật cùng job HR poll."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_push_with_claimed_job_updates_same_job(client):
    job = client.post("/api/attendance/sync-now", headers=_hr_headers(client)).json()
    job_id = job["id"]

    client.post(
        f"/api/integrations/mitapro/pending/{job_id}/claim",
        headers=_agent_headers(),
    )

    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "claimed_job_id": job_id,
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-08T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-08T17:00:00+07:00"},
            ],
        },
    )
    assert res.status_code == 200, res.text
    out = res.json()["job"]
    assert out["id"] == job_id
    assert out["status"] in ("success", "partial", "running")
    assert out["records_inserted"] >= 0

    listed = client.get("/api/integrations/sync-jobs?limit=5", headers=_hr_headers(client)).json()
    same = next((j for j in listed["items"] if j["id"] == job_id), None)
    assert same is not None
