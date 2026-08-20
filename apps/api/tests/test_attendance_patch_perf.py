"""Hàng rào: sửa ô công / gán nghỉ 1 NV không quét SQL theo số NV nhà máy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.test_employees_list_benchmark import EMP_COUNT, _seed_employees, _SqlCounter

MAX_PATCH_STATEMENTS = 80
MAX_PATCH_WRITES = 40
MAX_GET_GRID_STATEMENTS = 25
MAX_GET_TIMESHEETS_STATEMENTS = 15


def _hr_headers(client) -> dict[str, str]:
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_patch_day_cell_sql_khong_tang_theo_so_nv(client, db):
    _seed_employees(db, EMP_COUNT)
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    bind = db.get_bind()
    client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "5290",
            "work_date": "2025-10-10",
            "first_in": datetime(2025, 10, 10, 8, 0, tzinfo=VN).isoformat(),
            "last_out": datetime(2025, 10, 10, 17, 0, tzinfo=VN).isoformat(),
        },
    )

    with _SqlCounter(bind) as counter:
        res = client.patch(
            "/api/attendance/days/cell",
            headers=headers,
            json={
                "employee_code": "5290",
                "work_date": "2025-10-10",
                "leave_code": "ALE",
            },
        )
    assert res.status_code == 200, res.text
    assert res.json()["leave_code"] == "ALE"
    print(f"\n[PATCH days/cell leave] SQL {counter.summary()}")
    assert len(counter.writes) <= MAX_PATCH_WRITES, (
        f"PATCH 1 NV ghi quá nhiều (rebuild cả nhà máy?) — {counter.summary()}"
    )
    assert len(counter.statements) <= MAX_PATCH_STATEMENTS, (
        f"PATCH 1 NV số SQL tăng theo {EMP_COUNT} NV — {counter.summary()}"
    )


def test_get_days_grid_sql_khong_n_plus_1(client, db):
    _seed_employees(db, EMP_COUNT)
    headers = _hr_headers(client)
    client.get("/api/attendance/days/grid", headers=headers, params={"date": "2025-10-10"})

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get(
            "/api/attendance/days/grid",
            headers=headers,
            params={"date": "2025-10-10"},
        )
    assert res.status_code == 200, res.text
    assert len(res.json()) >= EMP_COUNT
    print(f"\n[GET days/grid] SQL {counter.summary()} rows={len(res.json())}")
    assert len(counter.writes) == 0, f"GET lưới ngày ghi DB — {counter.summary()}"
    assert len(counter.statements) <= MAX_GET_GRID_STATEMENTS, (
        f"GET lưới ngày N+1 — {counter.summary()}"
    )


def test_get_timesheets_one_employee_it_sql(client, db):
    _seed_employees(db, EMP_COUNT)
    headers = _hr_headers(client)
    VN = timezone(timedelta(hours=7))
    client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={
            "employee_code": "5290",
            "work_date": "2025-10-11",
            "first_in": datetime(2025, 10, 11, 8, 0, tzinfo=VN).isoformat(),
            "last_out": datetime(2025, 10, 11, 17, 0, tzinfo=VN).isoformat(),
        },
    )

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get(
            "/api/attendance/timesheets",
            headers=headers,
            params={"period": "2025-10", "employee_code": "5290"},
        )
    assert res.status_code == 200, res.text
    assert len(res.json()) == 1
    print(f"\n[GET timesheets?employee_code] SQL {counter.summary()}")
    assert len(counter.writes) == 0, f"GET timesheet 1 NV ghi DB — {counter.summary()}"
    assert len(counter.statements) <= MAX_GET_TIMESHEETS_STATEMENTS, (
        f"GET timesheet 1 NV quá nhiều SQL — {counter.summary()}"
    )
