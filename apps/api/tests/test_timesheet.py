"""P2.4 — timesheet tháng + điều chỉnh leave/OT tay."""

from app.core.config import get_settings


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_rebuild_timesheet_from_punches(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:01:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-01T17:05:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    rebuild = client.post(
        "/api/attendance/timesheets/rebuild",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["rows_upserted"] >= 1

    sheets = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert sheets.status_code == 200
    row = next(r for r in sheets.json() if r["employee_code"] == "5290")
    assert float(row["worked_days"]) == 1.0
    assert row["late_count"] == 1
    assert float(row["ot_hours_weekday"]) == 0.0  # 17:05 < 17:15 (ot_split grace)


def test_manual_leave_and_ot_adjustment(client):
    headers = _hr_headers(client)
    leaves = client.get("/api/attendance/leave-types", headers=headers)
    assert leaves.status_code == 200
    assert any(x["code"] == "ALE" for x in leaves.json())

    al = client.post(
        "/api/attendance/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "1514",
            "kind": "leave",
            "leave_code": "ALE",
            "days": "1.0",
            "note": "Nghỉ phép năm",
        },
    )
    assert al.status_code == 200, al.text
    assert al.json()["created_by"] == "hr.demo"

    ot = client.post(
        "/api/attendance/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "1514",
            "kind": "ot",
            "ot_type": "weekday",
            "ot_hours": "2",
            "note": "OT đăng ký",
        },
    )
    assert ot.status_code == 200

    sheets = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    ).json()
    row = next(r for r in sheets if r["employee_code"] == "1514")
    assert float(row["al_days"]) == 1.0
    assert float(row["ot_hours_weekday"]) == 2.0

    adj = client.get(
        "/api/attendance/adjustments",
        headers=headers,
        params={"period": "2025-10", "employee_code": "1514"},
    ).json()
    assert len(adj) >= 2

    deleted = client.delete(f"/api/attendance/adjustments/{al.json()['id']}", headers=headers)
    assert deleted.status_code == 200
    sheets2 = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    ).json()
    row2 = next(r for r in sheets2 if r["employee_code"] == "1514")
    assert float(row2["al_days"]) == 0.0


def test_pay_period_oct_2025_divisor(client):
    headers = _hr_headers(client)
    res = client.get("/api/attendance/pay-periods/2025-10", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "open"
    assert float(body["salary_divisor"]) == 26.0
