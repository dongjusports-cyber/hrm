"""3.2 — lọc chấm vân tay liên tục 60 giây."""

from datetime import date, datetime, time, timedelta, timezone

from app.core.config import get_settings
from app.modules.attendance.engine import Schedule, calculate_day
from app.modules.attendance.punch_dedupe import dedupe_punch_times

VN = timezone(timedelta(hours=7))


def _sched() -> Schedule:
    return Schedule(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(8, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(17, 0),
        grace_late_minutes=0,
        holiday_dates=set(),
    )


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_five_taps_within_60s_become_one_check_in():
    """24§ nghiệm thu: 5 lần bấm liên tiếp lúc 07:50 → một giờ vào."""
    base = datetime(2025, 10, 6, 7, 50, 0, tzinfo=VN)
    punches = [base + timedelta(seconds=i * 10) for i in range(5)]
    deduped = dedupe_punch_times(punches, window_seconds=60)
    assert deduped == [base]

    d = date(2025, 10, 6)
    r = calculate_day(punches, d, _sched())
    assert r.first_in == base
    assert r.last_out == base
    assert r.punch_count == 1


def test_morning_burst_and_evening_burst():
    morning = datetime(2025, 10, 7, 7, 50, 0, tzinfo=VN)
    morning_dup = morning + timedelta(seconds=15)
    evening = datetime(2025, 10, 7, 17, 0, 0, tzinfo=VN)
    evening_dup = evening + timedelta(seconds=20)
    punches = [morning, morning_dup, evening, evening_dup]

    deduped = dedupe_punch_times(punches, window_seconds=60)
    assert deduped == [morning, evening_dup]

    r = calculate_day(punches, date(2025, 10, 7), _sched())
    assert r.first_in == morning
    assert r.last_out == evening_dup
    assert r.punch_count == 2
    assert r.late_minutes == 0
    assert r.ot_minutes == 0


def test_punches_61_seconds_apart_not_merged():
    t1 = datetime(2025, 10, 8, 7, 50, 0, tzinfo=VN)
    t2 = t1 + timedelta(seconds=61)
    deduped = dedupe_punch_times([t1, t2], window_seconds=60)
    assert deduped == [t1, t2]


def test_recalculate_applies_dedupe(client):
    """Push 5 punch sát nhau → bảng công chỉ còn 1 mốc vào."""
    base = "2025-10-09T07:50:00+07:00"
    punches = [
        {"employee_code": "5290", "punch_time": base},
        {"employee_code": "5290", "punch_time": "2025-10-09T07:50:10+07:00"},
        {"employee_code": "5290", "punch_time": "2025-10-09T07:50:20+07:00"},
        {"employee_code": "5290", "punch_time": "2025-10-09T07:50:30+07:00"},
        {"employee_code": "5290", "punch_time": "2025-10-09T07:50:40+07:00"},
        {"employee_code": "5290", "punch_time": "2025-10-09T17:00:00+07:00"},
    ]
    res = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={"punches": punches},
    )
    assert res.status_code == 200, res.text

    headers = _hr_headers(client)
    recalc = client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-09", "to": "2025-10-09", "employee_code": "5290"},
    )
    assert recalc.status_code == 200

    day = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-09", "to": "2025-10-09", "employee_code": "5290"},
    ).json()[0]
    assert day["punch_count"] == 2
    assert day["first_in"].startswith("2025-10-09T07:50:00")
    assert day["last_out"].startswith("2025-10-09T17:00:00")
    assert float(day["worked_hours"]) == 8.0
