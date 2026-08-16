"""3.5 — timesheet_month_details theo category × segment."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.core.config import get_settings
from app.modules.attendance.models import AttendanceDay, TimesheetAdjustment
from app.modules.attendance.timesheet_details import aggregate_month_details
from app.modules.mdm.models import Employee


def _agent_headers():
    return {"X-Agent-Token": get_settings().agent_token}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _detail_map(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["category"], r["segment"]): r for r in rows}


def test_rebuild_creates_wt_and_ot_details(client):
    # 2025-10-14 = Thứ 3 (OT trên sổ); ra 17:20 → 20p OT (sau grace 17:15)
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-14T08:01:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-14T17:20:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/timesheets/rebuild",
        headers=headers,
        params={"period": "2025-10"},
    )
    details = client.get(
        "/api/attendance/timesheets/details",
        headers=headers,
        params={"period": "2025-10", "employee_code": "5290"},
    )
    assert details.status_code == 200, details.text
    m = _detail_map(details.json())
    assert ("WT", "official") in m
    assert float(m[("WT", "official")]["days"]) == 1.0
    assert ("OT", "official") in m
    assert float(m[("OT", "official")]["hours"]) == 0.33  # 20 phút


def test_rebuild_sunday_st_hours(client):
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
        "/api/attendance/timesheets/rebuild",
        headers=headers,
        params={"period": "2025-10"},
    )
    details = client.get(
        "/api/attendance/timesheets/details",
        headers=headers,
        params={"period": "2025-10", "employee_code": "5290"},
    ).json()
    m = _detail_map(details)
    assert ("ST", "official") in m
    assert float(m[("ST", "official")]["hours"]) == 4.0


def test_adjustment_abs_ale_detail(client):
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "1514",
            "kind": "leave",
            "leave_code": "ALE",
            "days": "1.5",
            "note": "Phép năm",
        },
    )
    details = client.get(
        "/api/attendance/timesheets/details",
        headers=headers,
        params={"period": "2025-10", "employee_code": "1514"},
    ).json()
    m = _detail_map(details)
    assert ("ABS_ALE", "official") in m
    assert float(m[("ABS_ALE", "official")]["days"]) == 1.5


def test_probation_segment_on_attendance_day(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "1643").one()
    emp.status = "probation"
    db.commit()

    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "1643", "punch_time": "2025-10-03T08:00:00+07:00"},
                {"employee_code": "1643", "punch_time": "2025-10-03T17:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/timesheets/rebuild",
        headers=headers,
        params={"period": "2025-10"},
    )
    details = client.get(
        "/api/attendance/timesheets/details",
        headers=headers,
        params={"period": "2025-10", "employee_code": "1643"},
    ).json()
    m = _detail_map(details)
    assert ("WT", "probation") in m
    assert float(m[("WT", "probation")]["days"]) == 1.0


def test_aggregate_unit(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    day = AttendanceDay(
        employee_id=emp.id,
        work_date=date(2025, 10, 1),
        is_workday=True,
        punch_count=2,
        worked_hours=Decimal("8"),
        ot_minutes=60,
        ot_on_books_minutes=60,
        ot_external_minutes=0,
        ot_type="weekday",
        segment="official",
        sunday_hours=Decimal("0"),
        holiday_hours=Decimal("0"),
    )
    buckets = aggregate_month_details([day], [], emp)
    assert buckets[("official", "WT")]["days"] == Decimal("1.00")
    assert buckets[("official", "OT")]["hours"] == Decimal("1.00")

    adj = TimesheetAdjustment(
        pay_period_id=uuid4(),
        employee_id=emp.id,
        kind="leave",
        leave_code="ALE",
        days=Decimal("2"),
    )
    buckets2 = aggregate_month_details([], [adj], emp)
    assert buckets2[("official", "ABS_ALE")]["days"] == Decimal("2.00")


def test_aggregate_half_day_leave_not_full_day(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    day = AttendanceDay(
        employee_id=emp.id,
        work_date=date(2025, 10, 23),
        is_workday=True,
        punch_count=2,
        worked_hours=Decimal("4"),
        leave_code="ALE",
        leave_days=Decimal("0.5"),
        ot_minutes=0,
        ot_on_books_minutes=0,
        ot_external_minutes=0,
        ot_type="weekday",
        segment="official",
    )
    buckets = aggregate_month_details([day], [], emp)
    assert buckets[("official", "ABS_ALE")]["days"] == Decimal("0.50")
    assert buckets[("official", "WT")]["days"] == Decimal("0.50")


def test_aggregate_sunday_ot_not_also_ot_ext(db):
    """QA-08: Chủ nhật chỉ ST, không cộng OT_EXT trùng giờ."""
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    day = AttendanceDay(
        employee_id=emp.id,
        work_date=date(2025, 10, 5),
        is_workday=False,
        punch_count=2,
        worked_hours=Decimal("4"),
        ot_minutes=240,
        ot_on_books_minutes=0,
        ot_external_minutes=240,
        ot_type="weekend",
        sunday_hours=Decimal("4"),
        holiday_hours=Decimal("0"),
        segment="official",
    )
    buckets = aggregate_month_details([day], [], emp)
    assert ("official", "ST") in buckets
    assert buckets[("official", "ST")]["hours"] == Decimal("4.00")
    assert ("official", "OT_EXT") not in buckets
    assert ("official", "OT") not in buckets
