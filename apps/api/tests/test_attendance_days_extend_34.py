"""3.4 — attendance_days mở rộng (21§21.5)."""

from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal

from app.core.config import get_settings
from app.modules.attendance.day_enrich import apply_calc_to_day_row, resolve_segment, resolve_work_shift_id
from app.modules.attendance.engine import DayCalcResult, Schedule
from app.modules.attendance.models import AttendanceDay
from app.modules.attendance.seed_shifts import ADMIN_SHIFT_CODE
from app.modules.mdm.models import Employee

VN = timezone(timedelta(hours=7))


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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


def test_resolve_segment():
    active = Employee(status="active")
    prob = Employee(status="probation")
    assert resolve_segment(active) == "official"
    assert resolve_segment(prob) == "probation"


def test_apply_calc_weekday_ot_night_zero():
    emp = Employee(status="active")
    row = AttendanceDay(employee_id=emp.id, work_date=date(2025, 10, 14))
    calc = DayCalcResult(
        work_date=date(2025, 10, 14),
        first_in=datetime(2025, 10, 14, 8, 0, tzinfo=VN),
        last_out=datetime(2025, 10, 14, 20, 0, tzinfo=VN),
        worked_hours=Decimal("8.0000"),
        late_minutes=0,
        early_minutes=0,
        ot_minutes=180,
        ot_on_books_minutes=180,
        ot_external_minutes=0,
        ot_type="weekday",
        punch_count=2,
        is_workday=True,
    )
    apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=ADMIN_SHIFT_CODE)
    assert row.source == "machine"
    assert row.segment == "official"
    assert row.work_shift_id == ADMIN_SHIFT_CODE
    assert row.night_hours == Decimal("0")
    assert row.ot_night_hours == Decimal("0")
    assert row.sunday_hours == Decimal("0")
    assert row.holiday_hours == Decimal("0")


def test_apply_calc_sunday_hours():
    emp = Employee(status="active")
    row = AttendanceDay(employee_id=emp.id, work_date=date(2025, 10, 5))
    calc = DayCalcResult(
        work_date=date(2025, 10, 5),
        first_in=datetime(2025, 10, 5, 8, 0, tzinfo=VN),
        last_out=datetime(2025, 10, 5, 12, 0, tzinfo=VN),
        worked_hours=Decimal("0"),
        late_minutes=0,
        early_minutes=0,
        ot_minutes=240,
        ot_on_books_minutes=0,
        ot_external_minutes=0,
        ot_type="weekend",
        punch_count=2,
        is_workday=False,
    )
    apply_calc_to_day_row(row, calc=calc, employee=emp, work_shift_id=ADMIN_SHIFT_CODE)
    assert row.sunday_hours == Decimal("4.00")
    assert row.holiday_hours == Decimal("0")


def test_recalculate_sets_34_columns(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-01T17:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-01", "to": "2025-10-01", "employee_code": "5290"},
    )
    day = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-01", "to": "2025-10-01", "employee_code": "5290"},
    ).json()[0]
    assert day["work_shift_id"] == ADMIN_SHIFT_CODE
    assert day["source"] == "machine"
    assert day["segment"] == "official"
    assert float(day["night_hours"]) == 0.0
    assert float(day["ot_night_hours"]) == 0.0
    assert day["is_locked"] is False


def test_recalculate_sunday_hours(client):
    """2025-10-05 = Chủ nhật — OT gom vào sunday_hours."""
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-05T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-05T12:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-05", "to": "2025-10-05", "employee_code": "5290"},
    )
    day = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-05", "to": "2025-10-05", "employee_code": "5290"},
    ).json()[0]
    assert day["ot_type"] == "weekend"
    assert float(day["sunday_hours"]) == 4.0
    assert float(day["holiday_hours"]) == 0.0
    assert int(day["ot_external_minutes"]) == 240
    assert int(day["ot_minutes"]) == 240


def test_locked_row_not_overwritten(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    wd = date(2025, 10, 20)
    locked_in = datetime(2025, 10, 20, 9, 0, 0, tzinfo=VN)
    row = AttendanceDay(
        employee_id=emp.id,
        work_date=wd,
        first_in=locked_in,
        last_out=locked_in,
        worked_hours=Decimal("1"),
        is_locked=True,
        note="HR khoá",
        source="manual",
        segment="official",
    )
    db.add(row)
    db.commit()

    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-20T08:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-20T17:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    recalc = client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-20", "to": "2025-10-20", "employee_code": "5290"},
    )
    assert recalc.status_code == 200
    assert recalc.json()["days_upserted"] == 0

    db.refresh(row)
    assert row.is_locked is True
    assert row.note == "HR khoá"
    assert row.source == "manual"
    assert row.worked_hours == Decimal("1")
    assert row.first_in is not None
    assert row.first_in.hour == 9 and row.first_in.minute == 0


def test_resolve_work_shift_id(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    shift_id = resolve_work_shift_id(db, emp, date(2025, 10, 1))
    assert shift_id == ADMIN_SHIFT_CODE
