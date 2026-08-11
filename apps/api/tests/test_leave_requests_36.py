"""3.6 — leave_requests + duyệt hàng loạt."""

from datetime import date

from app.modules.attendance.models import AttendanceDay, LeaveRequest


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _worker_headers(client, code="5290", password="1234"):
    token = client.post(
        "/api/worker/login", json={"employee_code": code, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_worker_submit_leave_request(client):
    headers = _worker_headers(client)
    res = client.post(
        "/api/worker/leave-requests",
        headers=headers,
        json={
            "leave_type_code": "ALE",
            "from_date": "2025-10-20",
            "to_date": "2025-10-21",
            "reason": "Việc gia đình",
            "submit": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "submitted"
    assert float(body["total_days"]) == 2.0
    assert body["leave_type_code"] == "ALE"


def test_hr_list_pending_queue(client):
    _worker_headers(client)
    client.post(
        "/api/worker/leave-requests",
        headers=_worker_headers(client, "1514"),
        json={
            "leave_type_code": "OFF",
            "from_date": "2025-11-01",
            "to_date": "2025-11-01",
            "reason": "Nghỉ bù",
            "submit": True,
        },
    )
    headers = _hr_headers(client)
    res = client.get("/api/attendance/leave-requests", headers=headers, params={"status": "submitted"})
    assert res.status_code == 200
    codes = {r["employee_code"] for r in res.json()}
    assert "5290" in codes or "1514" in codes


def test_bulk_approve_applies_leave_code(client, db):
    headers = _worker_headers(client, "5290")
    created = client.post(
        "/api/worker/leave-requests",
        headers=headers,
        json={
            "leave_type_code": "ALE",
            "from_date": "2025-10-22",
            "to_date": "2025-10-22",
            "reason": "1 ngày phép",
            "submit": True,
        },
    ).json()
    hr = _hr_headers(client)
    decide = client.post(
        "/api/attendance/leave-requests/bulk-decide",
        headers=hr,
        json={
            "request_ids": [created["id"]],
            "action": "approve",
            "decided_note": "OK",
        },
    )
    assert decide.status_code == 200, decide.text
    assert decide.json()["approved_count"] == 1

    from app.modules.mdm.models import Employee

    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    row = (
        db.query(AttendanceDay)
        .filter(AttendanceDay.employee_id == emp.id, AttendanceDay.work_date == date(2025, 10, 22))
        .one()
    )
    assert row.leave_code == "ALE"


def test_bulk_reject(client):
    headers = _worker_headers(client, "1643")
    created = client.post(
        "/api/worker/leave-requests",
        headers=headers,
        json={
            "leave_type_code": "TMP",
            "from_date": "2025-12-01",
            "to_date": "2025-12-02",
            "reason": "Hết hàng",
            "submit": True,
        },
    ).json()
    hr = _hr_headers(client)
    decide = client.post(
        "/api/attendance/leave-requests/bulk-decide",
        headers=hr,
        json={
            "request_ids": [created["id"]],
            "action": "reject",
            "decided_note": "Không duyệt",
        },
    )
    assert decide.status_code == 200
    assert decide.json()["rejected_count"] == 1


def test_overlap_rejected(client):
    headers = _worker_headers(client, "5321")
    payload = {
        "leave_type_code": "ALE",
        "from_date": "2025-10-10",
        "to_date": "2025-10-12",
        "reason": "Lần 1",
        "submit": True,
    }
    assert client.post("/api/worker/leave-requests", headers=headers, json=payload).status_code == 200
    dup = client.post("/api/worker/leave-requests", headers=headers, json=payload)
    assert dup.status_code == 400
    assert "trùng khoảng" in dup.json()["detail"].lower()


def test_ale_over_balance_skipped_on_bulk_approve(client, db):
    from app.modules.mdm.models import Employee

    emp = db.query(Employee).filter(Employee.employee_code == "1732").one()
    headers = _worker_headers(client, "1732")
    big = client.post(
        "/api/worker/leave-requests",
        headers=headers,
        json={
            "leave_type_code": "ALE",
            "from_date": "2025-10-01",
            "to_date": "2025-10-20",
            "reason": "20 ngày — vượt dư",
            "submit": True,
        },
    )
    assert big.status_code == 200
    req_id = big.json()["id"]
    hr = _hr_headers(client)
    decide = client.post(
        "/api/attendance/leave-requests/bulk-decide",
        headers=hr,
        json={"request_ids": [req_id], "action": "approve", "decided_note": ""},
    )
    assert decide.status_code == 200
    out = decide.json()
    assert out["approved_count"] == 0
    assert len(out["skipped"]) == 1
    assert out["skipped"][0]["employee_code"] == "1732"
    assert "vượt số dư" in out["skipped"][0]["reason"].lower()
