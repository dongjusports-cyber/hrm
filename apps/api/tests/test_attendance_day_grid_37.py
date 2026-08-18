"""3.7 — lưới bảng công ngày + bulk."""

from datetime import date, datetime, timezone, timedelta

from app.modules.attendance.models import AttendanceDay
from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _agent_headers():
    from app.core.config import get_settings

    return {"X-Agent-Token": get_settings().agent_token}


def test_days_grid_lists_employees(client):
    headers = _hr_headers(client)
    res = client.get(
        "/api/attendance/days/grid",
        headers=headers,
        params={"date": "2025-10-01"},
    )
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) >= 5
    codes = {r["employee_code"] for r in rows}
    assert "5290" in codes
    assert "team_code" in rows[0] or rows[0]["team_code"] is None


def test_days_grid_needs_action_filter(client):
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "5290", "punch_time": "2025-10-02T08:00:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    all_rows = client.get(
        "/api/attendance/days/grid",
        headers=headers,
        params={"date": "2025-10-02"},
    ).json()
    filtered = client.get(
        "/api/attendance/days/grid",
        headers=headers,
        params={"date": "2025-10-02", "needs_action_only": "true"},
    ).json()
    assert len(filtered) <= len(all_rows)
    row5290 = next(r for r in filtered if r["employee_code"] == "5290")
    assert row5290["needs_action"] is True
    assert row5290["row_flag"] in ("odd", "missing", "late", "early", "both")


def test_patch_day_cell_times(client):
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-03",
            "first_in": datetime(2025, 10, 3, 8, 0, tzinfo=VN).isoformat(),
            "last_out": datetime(2025, 10, 3, 17, 0, tzinfo=VN).isoformat(),
            "note": "Sửa lưới",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["employee_code"] == "1514"
    assert body["punch_count"] == 2
    assert body["source"] == "manual"


def test_patch_day_cell_in_only(client):
    """HR sửa một ô Vào (thiếu Ra) — Enter phải lưu, không 400."""
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-05",
            "first_in": datetime(2025, 10, 5, 8, 0, tzinfo=VN).isoformat(),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["punch_count"] == 1
    assert body["first_in"] is not None
    assert body["source"] == "manual"


def test_patch_day_cell_out_keeps_existing_in(client):
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    both = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-06",
            "first_in": datetime(2025, 10, 6, 8, 0, tzinfo=VN).isoformat(),
            "last_out": datetime(2025, 10, 6, 17, 0, tzinfo=VN).isoformat(),
        },
    )
    assert both.status_code == 200, both.text
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-06",
            "last_out": datetime(2025, 10, 6, 18, 0, tzinfo=VN).isoformat(),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["punch_count"] == 2
    assert body["last_out"].startswith("2025-10-06T18:00")
    assert "T08:00" in body["first_in"]


def test_patch_day_cell_clear_first_in(client):
    """Xóa ô Vào (Enter trống) — giữ giờ ra."""
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    both = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-08",
            "first_in": datetime(2025, 10, 8, 6, 13, tzinfo=VN).isoformat(),
            "last_out": datetime(2025, 10, 8, 17, 0, tzinfo=VN).isoformat(),
        },
    )
    assert both.status_code == 200, both.text
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-08",
            "clear_first_in": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["first_in"] is None
    assert body["last_out"] is not None
    assert "T17:00" in body["last_out"]
    assert body["source"] == "manual"


def test_patch_day_cell_clear_times(client):
    """Nút Xóa giờ — về 0 công, không còn vào/ra."""
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    both = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-09",
            "first_in": datetime(2025, 10, 9, 8, 0, tzinfo=VN).isoformat(),
            "last_out": datetime(2025, 10, 9, 17, 0, tzinfo=VN).isoformat(),
        },
    )
    assert both.status_code == 200, both.text
    assert float(both.json()["worked_hours"]) == 8.0
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-09",
            "clear_times": True,
            "note": "Xóa giờ sai",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["first_in"] is None
    assert body["last_out"] is None
    assert float(body["worked_hours"]) == 0
    assert body["punch_count"] == 0
    assert body["late_minutes"] == 0
    assert body["ot_minutes"] == 0
    assert body["note"] == "Xóa giờ sai"
    assert body["source"] == "manual"


def test_hr_supplement_out_survives_recalculate(client):
    """1519-style: máy chỉ có vào — HR Enter giờ ra — tính lại/tính lương không nuốt công."""
    client.post(
        "/api/integrations/mitapro/push",
        headers=_agent_headers(),
        json={
            "punches": [
                {"employee_code": "1514", "punch_time": "2025-10-07T07:38:00+07:00"},
            ]
        },
    )
    headers = _hr_headers(client)
    client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-07", "to": "2025-10-07", "employee_code": "1514"},
    )
    before = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-07", "to": "2025-10-07", "employee_code": "1514"},
    ).json()[0]
    assert float(before["worked_hours"]) == 0
    assert before["last_out"] is None

    patched = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "1514",
            "work_date": "2025-10-07",
            "last_out": "2025-10-07T17:00:00+07:00",
            "note": "Bổ sung công tay",
        },
    )
    assert patched.status_code == 200, patched.text
    assert float(patched.json()["worked_hours"]) == 8.0
    assert patched.json()["source"] == "manual"

    client.post(
        "/api/attendance/recalculate",
        headers=headers,
        json={"from": "2025-10-07", "to": "2025-10-07", "employee_code": "1514"},
    )
    after = client.get(
        "/api/attendance/days",
        headers=headers,
        params={"from": "2025-10-07", "to": "2025-10-07", "employee_code": "1514"},
    ).json()[0]
    assert float(after["worked_hours"]) == 8.0
    assert after["last_out"] is not None
    assert "T17:00" in after["last_out"]
    assert after["note"] == "Bổ sung công tay"
    assert after["source"] == "manual"


def test_bulk_set_leave_preview_and_apply(client, db):
    headers = _hr_headers(client)
    preview = client.post(
        "/api/attendance/days/bulk",
        headers=headers,
        json={
            "work_date": "2025-10-04",
            "employee_codes": ["1643", "5321"],
            "action": "set_leave",
            "leave_code": "OFF",
            "preview": True,
        },
    )
    assert preview.status_code == 200
    assert preview.json()["preview"] is True
    assert preview.json()["affected_count"] == 2

    apply = client.post(
        "/api/attendance/days/bulk",
        headers=headers,
        json={
            "work_date": "2025-10-04",
            "employee_codes": ["1643", "5321"],
            "action": "set_leave",
            "leave_code": "OFF",
            "preview": False,
        },
    )
    assert apply.status_code == 200
    assert apply.json()["affected_count"] == 2

    emp = db.query(Employee).filter(Employee.employee_code == "1643").one()
    row = (
        db.query(AttendanceDay)
        .filter(AttendanceDay.employee_id == emp.id, AttendanceDay.work_date == date(2025, 10, 4))
        .one()
    )
    assert row.leave_code == "OFF"


def test_locked_row_skipped_in_bulk(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    db.add(
        AttendanceDay(
            employee_id=emp.id,
            work_date=date(2025, 10, 10),
            is_locked=True,
            punch_count=2,
        )
    )
    db.commit()
    headers = _hr_headers(client)
    res = client.post(
        "/api/attendance/days/bulk",
        headers=headers,
        json={
            "work_date": "2025-10-10",
            "employee_codes": ["5290", "1514"],
            "action": "clear_note",
            "preview": True,
        },
    )
    assert res.status_code == 200
    skipped = res.json()["skipped"]
    assert any(s["employee_code"] == "5290" for s in skipped)


def test_days_grid_second_get_does_not_write(client, db):
    """GET lưới ngày không được ghi DB (cùng bài học GET /employees ghi-on-read)."""
    from sqlalchemy import event

    headers = _hr_headers(client)
    first = client.get(
        "/api/attendance/days/grid",
        headers=headers,
        params={"date": "2025-10-01"},
    )
    assert first.status_code == 200, first.text

    statements: list[str] = []

    def _record(conn, cursor, statement, params, context, executemany) -> None:
        statements.append(statement.strip().split(maxsplit=1)[0].upper())

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", _record)
    try:
        res = client.get(
            "/api/attendance/days/grid",
            headers=headers,
            params={"date": "2025-10-01"},
        )
    finally:
        event.remove(bind, "before_cursor_execute", _record)

    assert res.status_code == 200, res.text
    writes = [s for s in statements if s in ("INSERT", "UPDATE", "DELETE")]
    assert writes == [], f"GET /attendance/days/grid ghi DB: {writes} / {statements}"


def test_grid_ale_updates_timesheet_al_days(client):
    """HR gán phép năm trên lưới ngày → tổng hợp tháng cột phép = 1 (không chỉ điều chỉnh tay)."""
    headers = _hr_headers(client)
    res = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={"employee_code": "1732", "work_date": "2025-10-06", "leave_code": "ALE"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["leave_code"] == "ALE"
    assert body["source"] == "manual"

    sheets = client.get(
        "/api/attendance/timesheets",
        headers=headers,
        params={"period": "2025-10"},
    )
    assert sheets.status_code == 200, sheets.text
    row = next(r for r in sheets.json() if r["employee_code"] == "1732")
    assert float(row["al_days"]) == 1.0
