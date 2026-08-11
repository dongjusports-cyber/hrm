"""P1.3 — Calendar + auto salary_divisor (khớp bảng Hiến pháp 03§3.2)."""

from decimal import Decimal

from app.modules.calendar.engine import apply_divisor_rule, count_official_work_days


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_engine_oct_2025_27_to_26():
    official = count_official_work_days(
        year=2025,
        month=10,
        work_weekdays=[1, 2, 3, 4, 5, 6],
        holiday_dates=set(),
    )
    assert official == Decimal(27)
    assert apply_divisor_rule(official, {"when_official_eq": 27, "use_divisor": 26, "else": "official"}) == Decimal(
        26
    )
    assert apply_divisor_rule(official, {"source": "calendar_working_days", "cap": 26}) == Decimal(26)


def test_api_divisor_table_2025(client):
    headers = _admin_headers(client)
    cases = [
        (2025, 9, "26", "26"),
        (2025, 10, "27", "26"),
        (2025, 11, "25", "25"),
        (2025, 12, "27", "26"),
    ]
    for year, month, official, divisor in cases:
        res = client.get(f"/api/calendar/divisor?year={year}&month={month}", headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert Decimal(str(body["official_work_days"])) == Decimal(official)
        assert Decimal(str(body["salary_divisor"])) == Decimal(divisor)


def test_holiday_reduces_official_days(client):
    headers = _admin_headers(client)
    # Thêm lễ giữa tuần tháng 10 → official 26 → divisor 26 (không còn rule 27)
    add = client.post(
        "/api/calendar/holidays",
        headers=headers,
        json={"date": "2025-10-01", "name": "Nghỉ thử"},
    )
    assert add.status_code == 201, add.text
    res = client.get("/api/calendar/divisor?year=2025&month=10", headers=headers)
    assert res.status_code == 200
    assert Decimal(str(res.json()["official_work_days"])) == Decimal(26)
    assert Decimal(str(res.json()["salary_divisor"])) == Decimal(26)


def test_hr_can_read_divisor_not_write_week(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ok = client.get("/api/calendar/divisor?year=2025&month=10", headers=headers)
    assert ok.status_code == 200
    denied = client.put(
        "/api/calendar/work-week",
        headers=headers,
        json={"work_weekdays": [1, 2, 3, 4, 5]},
    )
    assert denied.status_code == 403
