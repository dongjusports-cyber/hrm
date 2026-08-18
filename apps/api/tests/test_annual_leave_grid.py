"""GET /api/employees/annual-leave — lưới phép năm live + file GenuSuite đối chiếu."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from app.modules.attendance.annual_leave_ledger import (
    annual_leave_snapshot,
    closed_accrual_months,
    prorate_al,
    sync_accrual_batch,
    timesheet_ale_used_ytd,
)
from app.modules.attendance.models import TimesheetMonth
from app.modules.mdm.annual_leave_snapshot import load_snapshot
from app.modules.mdm.models import Employee

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "annual_leave_snapshot.json"


def test_load_snapshot_5118(monkeypatch):
    monkeypatch.setenv("ANNUAL_LEAVE_SNAPSHOT", str(FIXTURE))
    payload = load_snapshot()
    assert payload["missing"] is False
    assert payload["year"] == 2026
    assert payload["employee_count"] == 2
    by = {r["employee_code"]: r for r in payload["employees"]}
    rec = by["5118"]
    assert rec["al_days"] == "16"
    assert rec["used"] == "5"
    assert rec["unused"] == "11"
    assert rec["accrued_months"] == 7
    assert rec["curr_al"] == "9.33"
    assert rec["curr_remaining"] == "4.33"
    newbie = by["9999"]
    assert newbie["al_days"] == "14"
    assert newbie["accrued_months"] == 4
    assert newbie["curr_al"] == "4.67"


def test_1519_july_proration():
    months = closed_accrual_months(date(2015, 3, 26), date(2026, 8, 17), 2026)
    assert months == 7
    curr = prorate_al(Decimal("16"), months)
    assert curr == Decimal("9.33")
    assert (curr - Decimal("5")).quantize(Decimal("0.01")) == Decimal("4.33")


def _hr_headers(client) -> dict[str, str]:
    token = client.post(
        "/api/auth/login",
        json={"username": "hr.demo", "password": "HrDemo@123456"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_annual_leave_grid_live(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2015, 3, 26)
    db.commit()

    res = client.get("/api/employees/annual-leave", headers=_hr_headers(client))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["missing"] is False
    assert body["employee_count"] >= 1
    rec = next(r for r in body["employees"] if r["employee_code"] == "5290")
    entitled = Decimal(str(rec["al_days"]))
    current = Decimal(str(rec["curr_al"]))
    used = Decimal(str(rec["used"]))
    remaining = Decimal(str(rec["curr_remaining"]))
    assert entitled == Decimal("16.00")
    as_of = date.today()
    months = closed_accrual_months(date(2015, 3, 26), as_of, as_of.year)
    assert rec["accrued_months"] == months
    assert current == prorate_al(entitled, months)
    assert remaining == (current - used).quantize(Decimal("0.01"))
    assert current != entitled or months >= 12


def test_get_annual_leave_grid_remaining_is_current_minus_used(client, db):
    res = client.get("/api/employees/annual-leave", headers=_hr_headers(client))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["employee_count"] >= 1
    for rec in body["employees"]:
        current = Decimal(str(rec["curr_al"]))
        used = Decimal(str(rec["used"]))
        remaining = Decimal(str(rec["curr_remaining"]))
        assert remaining == (current - used).quantize(Decimal("0.01")), rec["employee_code"]


def test_maternity_still_accrues_one_month_of_annual_leave(client, db):
    """Nghỉ thai sản không dừng phép năm: tháng đóng vẫn cộng (mốc/12), MLE không tính đã dùng."""
    headers = _hr_headers(client)
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9320",
            "full_name": "NV Thai san phep nam",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2015-03-26",
            "contract_signed_at": "2015-03-26",
            "status": "active",
            "si_enrolled": True,
        },
    )
    assert created.status_code == 201, created.text
    emp = db.query(Employee).filter(Employee.employee_code == "9320").one()
    as_of = date.today()
    before = annual_leave_snapshot(db, emp.id, as_of)

    mat_from = as_of - timedelta(days=80)
    mat_to = as_of + timedelta(days=40)
    mat = client.post(
        f"/api/employees/{emp.id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "MATERNITY",
            "hours_early": 0,
            "date_from": mat_from.isoformat(),
            "date_to": mat_to.isoformat(),
        },
    )
    assert mat.status_code == 201, mat.text

    after = annual_leave_snapshot(db, emp.id, as_of)
    assert after.entitled == before.entitled
    assert after.current == before.current
    assert after.used == before.used
    assert after.remaining == before.remaining
    months = closed_accrual_months(emp.join_date, as_of, as_of.year)
    assert after.current == prorate_al(after.entitled, months)
    assert after.current > 0
    assert timesheet_ale_used_ytd(db, emp.id, as_of) == Decimal("0.00")

    added = sync_accrual_batch(db, employee_ids=[emp.id], as_of=as_of)
    db.commit()
    assert added >= 1
    snap_after_write = annual_leave_snapshot(db, emp.id, as_of)
    assert snap_after_write.current == after.current

    grid = client.get("/api/employees/annual-leave", headers=headers)
    assert grid.status_code == 200, grid.text
    rec = next(r for r in grid.json()["employees"] if r["employee_code"] == "9320")
    assert rec["accrued_months"] == months
    assert Decimal(str(rec["curr_al"])) == after.current
    assert Decimal(str(rec["used"])) == Decimal("0.00")

    ts_rows = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.employee_id == emp.id)
        .all()
    )
    for ts in ts_rows:
        assert Decimal(str(ts.al_days or 0)) == Decimal("0"), "MLE không được cộng vào phép năm đã dùng"

