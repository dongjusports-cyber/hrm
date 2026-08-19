"""Chu kỳ: tích → giờ ra hết ca (17:00), đủ 8 giờ; danh sách + Excel."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.config import get_settings

VN = timezone(timedelta(hours=7))


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cycle_tick_bumps_out_to_shift_end(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-06T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-06T15:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    before = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-06", "to": "2025-10-06", "employee_code": "5290"},
    )
    assert before.status_code == 200, before.text
    assert before.json()
    assert Decimal(str(before.json()[0]["worked_hours"])) < Decimal("8")
    assert before.json()[0]["early_minutes"] > 0

    ticked = client.patch(
        "/api/attendance/days/cycle",
        headers=headers,
        json={"employee_code": "5290", "work_date": "2025-10-06", "cycle_leave": True},
    )
    assert ticked.status_code == 200, ticked.text
    body = ticked.json()
    assert body["cycle_leave"] is True
    assert body["early_minutes"] == 0
    assert Decimal(str(body["worked_hours"])) >= Decimal("8")
    assert "+07:00" in body["last_out"]
    out = datetime.fromisoformat(body["last_out"].replace("Z", "+00:00")).astimezone(VN)
    assert (out.hour, out.minute) == (17, 0)

    listed = client.get(
        "/api/attendance/cycle-leave",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert any(r["employee_code"] == "5290" and r["work_date"] == "2025-10-06" for r in rows)

    xlsx = client.get(
        "/api/attendance/cycle-leave.xlsx",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert xlsx.status_code == 200, xlsx.text
    assert xlsx.content[:2] == b"PK"

    off = client.patch(
        "/api/attendance/days/cycle",
        headers=headers,
        json={"employee_code": "5290", "work_date": "2025-10-06", "cycle_leave": False},
    )
    assert off.status_code == 200, off.text
    assert off.json()["cycle_leave"] is False
    out2 = datetime.fromisoformat(off.json()["last_out"].replace("Z", "+00:00")).astimezone(VN)
    assert (out2.hour, out2.minute) == (17, 0)


def test_cycle_requires_first_in(client):
    headers = _hr_headers(client)
    r = client.patch(
        "/api/attendance/days/cycle",
        headers=headers,
        json={"employee_code": "5290", "work_date": "2025-10-07", "cycle_leave": True},
    )
    assert r.status_code == 400
    assert "giờ vào" in r.json()["detail"]
