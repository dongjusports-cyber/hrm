"""Bước D — API chế độ về sớm (Thai sản / Nuôi con) 22§22.14."""

from datetime import date, timedelta
from decimal import Decimal


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_employee(client, headers, code: str) -> str:
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": f"NV WT {code}",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2020-01-15",
            "contract_signed_at": "2020-01-15",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_create_list_and_flag(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9301")
    today = date.today()
    body = {
        "regime_type": "CHILD",
        "hours_early": 2,
        "date_from": today.isoformat(),
        "date_to": (today + timedelta(days=30)).isoformat(),
        "note": "Nuôi con nhỏ",
    }
    res = client.post(f"/api/employees/{emp_id}/wt-regimes", headers=headers, json=body)
    assert res.status_code == 201, res.text
    r = res.json()
    assert r["regime_type"] == "CHILD"
    assert r["hours_early"] == 2
    assert r["ended_at"] is None

    listed = client.get(f"/api/employees/{emp_id}/wt-regimes", headers=headers).json()
    assert len(listed) == 1

    # Cờ wt_regime_active bật trên hồ sơ + tab «Chế độ đặc biệt»
    detail = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    assert detail["wt_regime_active"] is True
    special = client.get("/api/employees?status=special_regime", headers=headers).json()
    assert "9301" in {e["employee_code"] for e in special}
    row = next(e for e in special if e["employee_code"] == "9301")
    assert row["wt_regime_type"] == "CHILD"
    assert row["wt_regime_date_from"] == today.isoformat()
    assert row["si_base"] is not None


def test_validation_errors(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9302")
    today = date.today()

    # date_from quá khứ → 400 tiếng Việt
    past = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": (today - timedelta(days=1)).isoformat(),
            "date_to": (today + timedelta(days=10)).isoformat(),
        },
    )
    assert past.status_code == 400
    assert "hôm nay" in past.json()["detail"]

    # date_to < date_from → 400
    bad_range = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": (today + timedelta(days=10)).isoformat(),
            "date_to": (today + timedelta(days=5)).isoformat(),
        },
    )
    assert bad_range.status_code == 400


def test_overlap_rejected_then_end_frees(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9303")
    today = date.today()
    first = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=60)).isoformat(),
        },
    )
    assert first.status_code == 201, first.text
    rid = first.json()["id"]

    # Chuyển giai đoạn: tự cắt date_to cũ = ngày trước ngày bắt đầu mới
    nxt = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": (today + timedelta(days=10)).isoformat(),
            "date_to": (today + timedelta(days=20)).isoformat(),
        },
    )
    assert nxt.status_code == 201, nxt.text
    listed = client.get(f"/api/employees/{emp_id}/wt-regimes", headers=headers).json()
    preg = next(r for r in listed if r["id"] == rid)
    assert preg["date_to"] == (today + timedelta(days=9)).isoformat()

    # PATCH: đổi hours_early + date_to trên giai đoạn CHILD
    child_id = nxt.json()["id"]
    patched = client.patch(
        f"/api/employees/{emp_id}/wt-regimes/{child_id}",
        headers=headers,
        json={"hours_early": 3, "date_to": (today + timedelta(days=90)).isoformat()},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["hours_early"] == 3

    # End → ended_at set, date_to = hôm nay (nếu CHILD đã bắt đầu) hoặc kẹp date_from
    ended = client.post(f"/api/employees/{emp_id}/wt-regimes/{child_id}/end", headers=headers)
    assert ended.status_code == 200, ended.text
    assert ended.json()["ended_at"] is not None

    # Thêm mới sau khi đã chấm dứt → 201
    again = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=15)).isoformat(),
        },
    )
    assert again.status_code == 201, again.text


def test_maternity_stage_mle_and_cut(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9304")
    today = date.today()
    preg = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=90)).isoformat(),
        },
    )
    assert preg.status_code == 201, preg.text

    mat_from = today + timedelta(days=7)
    mat_to = today + timedelta(days=37)
    mat = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "MATERNITY",
            "hours_early": 0,
            "date_from": mat_from.isoformat(),
            "date_to": mat_to.isoformat(),
        },
    )
    assert mat.status_code == 201, mat.text
    assert mat.json()["hours_early"] == 0

    listed = client.get(f"/api/employees/{emp_id}/wt-regimes", headers=headers).json()
    old = next(r for r in listed if r["id"] == preg.json()["id"])
    assert old["date_to"] == (mat_from - timedelta(days=1)).isoformat()

    days = client.get(
        "/api/attendance/days",
        headers=headers,
        params={
            "from": mat_from.isoformat(),
            "to": mat_from.isoformat(),
            "employee_code": "9304",
        },
    )
    assert days.status_code == 200, days.text
    body = days.json()
    assert body, "phải có dòng công ngày bắt đầu nghỉ thai sản"
    assert body[0]["leave_code"] == "MLE"

    child_from = today + timedelta(days=20)
    child = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": child_from.isoformat(),
            "date_to": (child_from + timedelta(days=60)).isoformat(),
        },
    )
    assert child.status_code == 201, child.text
    listed2 = client.get(f"/api/employees/{emp_id}/wt-regimes", headers=headers).json()
    mat_row = next(r for r in listed2 if r["id"] == mat.json()["id"])
    assert mat_row["date_to"] == (child_from - timedelta(days=1)).isoformat()


def test_maternity_allows_past_start(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9305")
    today = date.today()
    past = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "MATERNITY",
            "hours_early": 0,
            "date_from": (today - timedelta(days=10)).isoformat(),
            "date_to": (today + timedelta(days=170)).isoformat(),
        },
    )
    assert past.status_code == 201, past.text
    detail = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    assert detail["wt_regime_type"] == "MATERNITY"
    assert detail["effective_status"] == "maternity"
    mat_tab = client.get("/api/employees?status=maternity", headers=headers).json()
    assert "9305" in {e["employee_code"] for e in mat_tab}


def test_maternity_pauses_si_on_calculate(client, db):
    from app.modules.attendance.models import TimesheetMonth
    from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
    from app.modules.mdm.models import Employee
    from app.modules.payroll import service as payroll_service

    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    mat = client.post(
        f"/api/employees/{emp.id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "MATERNITY",
            "hours_early": 0,
            "date_from": "2025-10-01",
            "date_to": "2025-10-31",
        },
    )
    assert mat.status_code == 201, mat.text

    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    pay = ensure_pay_period(db, "2025-10")
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("0")
    ts.al_days = Decimal("0")
    db.commit()

    def _rebuild_noop(db_sess, period, *, recalc_days=True):
        ensure_pay_period(db_sess, period)
        return type(
            "R",
            (),
            {
                "rows_upserted": 1,
                "message": "noop",
                "period": period,
                "pay_period_id": pay.id,
            },
        )()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _rebuild_noop
    try:
        res = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    finally:
        payroll_service.rebuild_timesheets = original

    assert res.status_code == 200, res.text
    row = next(p for p in res.json()["payslips"] if p["employee_code"] == "5290")
    assert Decimal(str(row["bhxh"])) == Decimal("0")
    assert Decimal(str(row["bhyt"])) == Decimal("0")
    assert Decimal(str(row["bhtn"])) == Decimal("0")
    assert Decimal(str(row["union_fee"])) == Decimal("0")

