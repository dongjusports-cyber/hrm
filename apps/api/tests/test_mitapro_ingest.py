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


def test_duplicate_push_still_rebuilds_attendance_days(client, db):
    """Agent lặp cửa sổ (bỏ trùng) vẫn tính lại ngày công — không chờ nút Đồng bộ."""
    from datetime import date

    from app.modules.attendance.models import AttendanceDay
    from app.modules.mdm.models import Employee

    payload = {
        "punches": [
            {"employee_code": "5290", "punch_time": "2025-10-03T08:00:00+07:00"},
            {"employee_code": "5290", "punch_time": "2025-10-03T17:00:00+07:00"},
        ],
        "synced_from": "2025-10-03T00:00:00+07:00",
        "synced_to": "2025-10-03T23:59:59+07:00",
    }
    first = client.post("/api/integrations/mitapro/push", headers=_agent_headers(), json=payload)
    assert first.status_code == 200, first.text
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    days = db.query(AttendanceDay).filter(AttendanceDay.employee_id == emp.id).all()
    for row in days:
        db.delete(row)
    db.commit()
    assert db.query(AttendanceDay).filter(AttendanceDay.employee_id == emp.id).count() == 0

    second = client.post("/api/integrations/mitapro/push", headers=_agent_headers(), json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["job"]["records_inserted"] == 0
    db.expire_all()
    restored = (
        db.query(AttendanceDay)
        .filter(AttendanceDay.employee_id == emp.id, AttendanceDay.work_date == date(2025, 10, 3))
        .one_or_none()
    )
    assert restored is not None
    assert (restored.punch_count or 0) >= 1


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


def test_push_patrol_guard_200_ignored(client):
    """MSNV 200* — bảo vệ tuần: không lưu, không cảnh báo partial."""
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "2005", "punch_time": "2025-10-03T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-03T08:01:00+07:00"},
            ]
        },
    )
    assert res.status_code == 200, res.text
    job = res.json()["job"]
    assert job["status"] == "success"
    assert job["records_inserted"] == 1
    assert "2005" not in job["message"]
    assert "bảo vệ tuần" in job["message"]

    headers = _hr_headers(client)
    ul = client.get("/api/integrations/punches/unlinked?limit=20", headers=headers).json()
    assert "2005" not in {i["employee_code"] for i in ul["items"]}


def test_push_naive_punch_time_treated_as_vn(client, db):
    """Mitapro/Agent thiếu TZ — coi là giờ VN (+07), không UTC."""
    from app.modules.integration.models import AttendancePunch
    from app.modules.attendance.engine import to_vn

    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-06T08:15:00"},
                {"employee_code": "5290", "punch_time": "2025-10-06T17:10:00"},
            ]
        },
    )
    assert res.status_code == 200, res.text
    row = (
        db.query(AttendancePunch)
        .filter(
            AttendancePunch.employee_code == "5290",
            AttendancePunch.punch_time >= "2025-10-06",
        )
        .order_by(AttendancePunch.punch_time.asc())
        .first()
    )
    assert row is not None
    assert to_vn(row.punch_time).hour == 8
    assert to_vn(row.punch_time).minute == 15


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
