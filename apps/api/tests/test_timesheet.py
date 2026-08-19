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
    # 8:01–17:05 → 7.9833h / 8 = 0.9979 → phiếu hiện 0.99 (làm tròn xuống 2 số)
    assert float(row["worked_days"]) == 0.99
    assert row["late_count"] == 1
    assert float(row["ot_hours_weekday"]) == 0.0  # 17:05 trong nghỉ cơm 17:00–17:30


def test_work_days_from_hours_examples():
    from decimal import Decimal

    from app.modules.attendance.timesheet_details import work_days_from_hours

    assert work_days_from_hours(Decimal("8")) == Decimal("1.0000")
    assert work_days_from_hours(Decimal("4")) == Decimal("0.5000")
    assert work_days_from_hours(Decimal("3.42")) == Decimal("0.4275")
    assert work_days_from_hours(0) == Decimal("0")


def test_rebuild_afternoon_only_half_day(client):
    """Chỉ chiều 13:00–17:00 → 0.5 ngày công trên phiếu."""
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-02T13:00:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-02T17:00:00+07:00"},
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
    sheets = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    ).json()
    row = next(r for r in sheets if r["employee_code"] == "5290")
    assert float(row["worked_days"]) == 0.5
    assert row["late_count"] == 1


def test_rebuild_sunday_ot_goes_to_external(client):
    """Chủ nhật 4 giờ → OT ngoài (ATM) + giữ ot_hours_weekend để hệ số 2."""
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
    rebuild = client.post(
        "/api/attendance/timesheets/rebuild",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert rebuild.status_code == 200, rebuild.text
    sheets = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert sheets.status_code == 200
    row = next(r for r in sheets.json() if r["employee_code"] == "5290")
    assert float(row["ot_hours_weekend"]) == 4.0
    assert float(row["ot_hours_holiday"]) == 0.0
    assert float(row["ot_hours_external"]) == 4.0
    assert float(row["ot_hours_weekday"]) == 0.0


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
    client.post("/api/attendance/timesheets/rebuild", headers=headers, params={"period": "2025-10"})
    res = client.get("/api/attendance/pay-periods/2025-10", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "open"
    assert float(body["salary_divisor"]) == 26.0


def test_get_timesheets_does_not_refresh_open_divisor(client, db):
    """QA-07: mở bảng công (GET) không UPDATE lại kỳ lương đang mở."""
    from decimal import Decimal

    from app.modules.attendance.models import PayPeriod
    from app.modules.attendance.timesheet import ensure_pay_period

    pay = ensure_pay_period(db, "2025-10", refresh_open=True)
    pay.salary_divisor = Decimal("99")
    db.commit()

    headers = _hr_headers(client)
    res = client.get("/api/attendance/timesheets", headers=headers, params={"period": "2025-10"})
    assert res.status_code == 200, res.text

    db.expire_all()
    again = db.query(PayPeriod).filter(PayPeriod.id == pay.id).one()
    assert Decimal(again.salary_divisor) == Decimal("99")


def test_ingest_rebuilds_only_employees_with_punches(client, db):
    """Mitapro push không tổng hợp cả nhà máy — chỉ NV có vân tay trong khoảng ngày."""
    from app.modules.attendance.models import TimesheetMonth
    from app.modules.mdm.models import Employee

    active_n = (
        db.query(Employee)
        .filter(Employee.deleted_at.is_(None), Employee.status == "active")
        .count()
    )
    assert active_n > 1

    push = client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:01:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-01T17:05:00+07:00"},
            ]
        },
    )
    assert push.status_code == 200, push.text

    db.expire_all()
    rows = db.query(TimesheetMonth).all()
    assert len(rows) == 1, f"ingest rebuild cả nhà máy: {len(rows)} dòng / {active_n} NV active"

    headers = _hr_headers(client)
    sheets = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert sheets.status_code == 200, sheets.text
    codes = {r["employee_code"] for r in sheets.json()}
    assert codes == {"5290"}


def test_list_timesheets_filter_employee_code(client):
    """Sau sửa 1 NV, UI chỉ GET timesheet NV đó — không kéo cả nhà máy."""
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-01T08:01:00+07:00"},
                {"employee_code": "5290", "punch_time": "2025-10-01T17:05:00+07:00"},
                {"employee_code": "1514", "punch_time": "2025-10-01T08:00:00+07:00"},
                {"employee_code": "1514", "punch_time": "2025-10-01T17:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post("/api/attendance/timesheets/rebuild", headers=headers, params={"period": "2025-10"})
    all_rows = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert all_rows.status_code == 200
    assert len(all_rows.json()) >= 2
    one = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10", "employee_code": "5290"},
    )
    assert one.status_code == 200, one.text
    body = one.json()
    assert len(body) == 1
    assert body[0]["employee_code"] == "5290"
