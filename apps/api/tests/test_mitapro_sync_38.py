"""3.8 — màn Đồng bộ Mitapro: sync_jobs, khoảng ngày, punch chưa khớp."""

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.modules.integration.models import AttendancePunch, SyncJob


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


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def test_list_sync_jobs(client):
    headers = _hr_headers(client)
    client.post("/api/attendance/sync-now", headers=headers)
    res = client.get("/api/integrations/sync-jobs?limit=10", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
    assert "status" in body["items"][0]
    assert "records_inserted" in body["items"][0]


def test_sync_range_creates_requested_job(client):
    headers = _hr_headers(client)
    res = client.post(
        "/api/attendance/sync-range",
        headers=headers,
        json={"from": "2025-10-01", "to": "2025-10-07"},
    )
    assert res.status_code == 200, res.text
    job = res.json()
    assert job["status"] == "requested"
    assert job["sync_date_from"] == "2025-10-01"
    assert job["sync_date_to"] == "2025-10-07"

    pending = client.get("/api/integrations/mitapro/pending", headers=_agent_headers())
    ids = {j["id"] for j in pending.json()}
    assert job["id"] in ids


def test_sync_range_rejects_invalid(client):
    headers = _hr_headers(client)
    bad = client.post(
        "/api/attendance/sync-range",
        headers=headers,
        json={"from": "2025-10-10", "to": "2025-10-01"},
    )
    assert bad.status_code == 422


def test_status_stale_fields(client, db):
    headers = _hr_headers(client)
    old = datetime.now(timezone.utc) - timedelta(hours=30)
    db.add(
        AttendancePunch(
            employee_code="5290",
            punch_time=old,
            source="mitapro",
        )
    )
    db.commit()

    st = client.get("/api/integrations/status", headers=headers).json()
    assert "stale_warning" in st
    assert "hours_since_data" in st
    assert st["stale_threshold_hours"] == 24
    assert st["stale_warning"] is True


def test_unlinked_in_sync_flow(client):
    headers = _hr_headers(client)
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [{"employee_code": "777777", "punch_time": "2025-10-08T08:00:00+07:00"}],
        },
    )
    ul = client.get("/api/integrations/punches/unlinked?limit=5", headers=headers).json()
    assert ul["total"] >= 1
    codes = {i["employee_code"] for i in ul["items"]}
    assert "777777" in codes


def test_relink_punches_admin(client, db):
    db.add(
        AttendancePunch(
            employee_code="5290",
            employee_id=None,
            punch_time=datetime(2025, 10, 9, 8, 0, tzinfo=timezone.utc),
            source="mitapro",
        )
    )
    db.commit()

    res = client.post("/api/integrations/punches/relink", headers=_admin_headers(client))
    assert res.status_code == 200, res.text
    assert res.json()["updated"] >= 1

    row = (
        db.query(AttendancePunch)
        .filter(AttendancePunch.employee_code == "5290", AttendancePunch.employee_id.isnot(None))
        .first()
    )
    assert row is not None
