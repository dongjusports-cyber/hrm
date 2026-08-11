"""R3 — rà soát thiếu punch + sửa tay ngày công."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_review_flags_odd_punch_and_manual_fix(client):
    # 1 punch → odd
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    rev = client.get("/api/attendance/review", headers=headers, params={"period": "2025-10"})
    assert rev.status_code == 200, rev.text
    body = rev.json()
    assert body["odd_punch"] >= 1
    assert any(
        i["issue_type"] == "odd_punch" and i["employee_code"] == "5290" and i["work_date"] == "2025-10-01"
        for i in body["issues"]
    )

    fixed = client.patch(
        "/api/attendance/days/manual",
        headers=headers,
        json={
            "employee_code": "5290",
            "work_date": "2025-10-01",
            "first_in": "2025-10-01T08:00:00+07:00",
            "last_out": "2025-10-01T17:00:00+07:00",
            "note": "bù punch ra",
        },
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["punch_count"] >= 2

    rev2 = client.get("/api/attendance/review", headers=headers, params={"period": "2025-10"}).json()
    assert not any(
        i["issue_type"] == "odd_punch"
        and i["employee_code"] == "5290"
        and i["work_date"] == "2025-10-01"
        for i in rev2["issues"]
    )


def test_manual_requires_both_times(client):
    headers = _hr_headers(client)
    r = client.patch(
        "/api/attendance/days/manual",
        headers=headers,
        json={
            "employee_code": "5290",
            "work_date": "2025-10-03",
            "first_in": "2025-10-03T08:00:00+07:00",
            "last_out": None,
        },
    )
    assert r.status_code == 400
    assert "Trợ Lý AI" in r.json()["detail"]


def test_adjustment_writes_audit(client):
    headers = _hr_headers(client)
    # admin for blackbox
    admin = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    admin_h = {"Authorization": f"Bearer {admin}"}

    created = client.post(
        "/api/attendance/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "1514",
            "kind": "leave",
            "leave_code": "ALE",
            "days": "1",
            "note": "test audit",
        },
    )
    assert created.status_code == 200, created.text

    box = client.get("/api/audit/blackbox", headers=admin_h, params={"limit": 50})
    assert box.status_code == 200
    actions = [a["action"] for a in box.json()["actions"]]
    assert "attendance.adjust.create" in actions
