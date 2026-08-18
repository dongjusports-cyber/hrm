"""3.3 — tính công một ngày (ca 08–17, dung sai 0 giây, OT sau 17:00)."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.core.config import get_settings
from app.modules.attendance.engine import Schedule, calculate_day

VN = timezone(timedelta(hours=7))


def _sched(**kwargs) -> Schedule:
    base = dict(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(8, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(17, 0),
        grace_late_minutes=0,
        holiday_dates=set(),
        grace_late_seconds=0,
        grace_early_seconds=0,
    )
    base.update(kwargs)
    return Schedule(**base)


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_not_late_at_075959():
    d = date(2025, 10, 10)
    punches = [
        datetime(2025, 10, 10, 7, 59, 59, tzinfo=VN),
        datetime(2025, 10, 10, 17, 0, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.late_minutes == 0
    assert r.worked_hours == Decimal("8.0000")


def test_late_at_080001():
    d = date(2025, 10, 15)  # Thứ 4
    punches = [
        datetime(2025, 10, 15, 8, 0, 1, tzinfo=VN),
        datetime(2025, 10, 15, 17, 0, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.late_minutes == 1


def test_out_at_2000_full_day_and_ot_3h():
    """24§ nghiệm thu: ra 20:00 (sau 17:30) → công 8h + OT 180 phút từ 17:00."""
    d = date(2025, 10, 14)  # Thứ 3
    punches = [
        datetime(2025, 10, 14, 8, 0, 0, tzinfo=VN),
        datetime(2025, 10, 14, 20, 0, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.worked_hours == Decimal("8.0000")
    assert r.ot_minutes == 180
    assert r.ot_on_books_minutes == 180
    assert r.late_minutes == 0
    assert r.early_minutes == 0


def test_early_one_second_before_shift_end():
    d = date(2025, 10, 16)  # Thứ 5
    punches = [
        datetime(2025, 10, 16, 8, 0, 0, tzinfo=VN),
        datetime(2025, 10, 16, 16, 59, 59, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.early_minutes == 1


def test_two_pre_shift_taps_not_checkout():
    """Hai lần bấm trước 08:00 — chỉ giữ giờ vào sớm nhất, không coi lần sau là ra."""
    d = date(2026, 8, 13)
    punches = [
        datetime(2026, 8, 13, 6, 58, 45, tzinfo=VN),
        datetime(2026, 8, 13, 7, 18, 59, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.first_in == punches[0]
    assert r.last_out is None
    assert r.worked_hours == Decimal("0")
    assert r.punch_count == 2


def test_pre_shift_plus_shift_start_not_checkout():
    """07:54 + 08:00 — cả hai là vào, không ghi 08:00 là ra."""
    d = date(2026, 8, 13)
    punches = [
        datetime(2026, 8, 13, 7, 54, 56, tzinfo=VN),
        datetime(2026, 8, 13, 8, 0, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.first_in == punches[0]
    assert r.last_out is None


def test_morning_in_and_early_leave_after_noon_break():
    d = date(2025, 10, 17)
    punches = [
        datetime(2025, 10, 17, 8, 0, 0, tzinfo=VN),
        datetime(2025, 10, 17, 12, 30, 0, tzinfo=VN),
    ]
    r = calculate_day(punches, d, _sched())
    assert r.first_in == punches[0]
    assert r.last_out == punches[1]


def test_recalculate_out_2000(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-14T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-14T20:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-14", "to": "2025-10-14", "employee_code": "5290"},
    )
    day = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-14", "to": "2025-10-14", "employee_code": "5290"},
    ).json()[0]
    assert float(day["worked_hours"]) == 8.0
    assert day["ot_minutes"] == 180
    assert day["ot_on_books_minutes"] == 180
