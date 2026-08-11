"""P2.2 — Agent poll / claim pending sync jobs."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_pending_claim_flow(client):
    # HR bấm Đồng bộ ngay
    job = client.post("/api/attendance/sync-now", headers=_hr_headers(client)).json()
    assert job["status"] == "requested"

    pending = client.get("/api/integrations/mitapro/pending", headers=_agent_headers())
    assert pending.status_code == 200
    ids = {j["id"] for j in pending.json()}
    assert job["id"] in ids

    claimed = client.post(
        f"/api/integrations/mitapro/pending/{job['id']}/claim",
        headers=_agent_headers(),
    )
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "running"

    # Claim lần 2 → 404
    again = client.post(
        f"/api/integrations/mitapro/pending/{job['id']}/claim",
        headers=_agent_headers(),
    )
    assert again.status_code == 404
