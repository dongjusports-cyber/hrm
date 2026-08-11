"""3.1 — attendance_punches employee_id, direction, sync_job_id."""

from uuid import UUID

from app.core.config import get_settings
from app.modules.integration.models import AttendancePunch


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_push_sets_employee_id_and_sync_job(client, db):
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {
                    "employee_code": "5290",
                    "punch_time": "2025-10-03T08:00:00+07:00",
                    "direction": "IN",
                },
                {
                    "employee_code": "5290",
                    "punch_time": "2025-10-03T17:00:00+07:00",
                    "direction": "OUT",
                },
            ],
        },
    )
    assert res.status_code == 200, res.text
    job_id = UUID(res.json()["job"]["id"])

    rows = (
        db.query(AttendancePunch)
        .filter(AttendancePunch.punch_time >= "2025-10-03")
        .order_by(AttendancePunch.punch_time.asc())
        .all()
    )
    day_rows = [r for r in rows if r.employee_code == "5290" and r.sync_job_id == job_id]
    assert len(day_rows) == 2
    assert all(r.employee_id is not None for r in day_rows)
    assert day_rows[0].direction == "IN"
    assert day_rows[1].direction == "OUT"


def test_unknown_msnv_null_employee_id(client, db):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [{"employee_code": "888888", "punch_time": "2025-10-04T08:00:00+07:00"}],
        },
    )
    row = (
        db.query(AttendancePunch)
        .filter(AttendancePunch.employee_code == "888888")
        .one_or_none()
    )
    assert row is not None
    assert row.employee_id is None


def test_unlinked_list_and_status(client):
    headers = _hr_headers(client)
    st = client.get("/api/integrations/status", headers=headers)
    assert st.status_code == 200
    assert "punch_unlinked_count" in st.json()

    unlinked = client.get("/api/integrations/punches/unlinked?limit=10", headers=headers)
    assert unlinked.status_code == 200
    assert "total" in unlinked.json()
    assert "items" in unlinked.json()


def test_direction_from_raw(client, db):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {
                    "employee_code": "5290",
                    "punch_time": "2025-10-05T08:01:00+07:00",
                    "raw": {"in_out": "IN"},
                },
            ],
        },
    )
    row = (
        db.query(AttendancePunch)
        .filter(AttendancePunch.employee_code == "5290", AttendancePunch.direction == "IN")
        .order_by(AttendancePunch.id.desc())
        .first()
    )
    assert row is not None
