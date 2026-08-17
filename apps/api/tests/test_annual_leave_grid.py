"""GET /api/employees/annual-leave — lưới phép năm từ snapshot GenuSuite."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.modules.mdm.annual_leave_snapshot import (
    closed_accrual_months,
    load_snapshot,
    prorate_al,
)

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
    assert rec["used_by_month"]["jun"] == "2"


def test_1519_july_proration():
    months = closed_accrual_months(date(2015, 3, 26), date(2026, 8, 17), 2026)
    assert months == 7
    curr = prorate_al(Decimal("16"), months)
    assert curr == Decimal("9.33")
    assert (curr - Decimal("5")).quantize(Decimal("0.01")) == Decimal("4.33")


def test_get_annual_leave_grid_hr(client, monkeypatch):
    monkeypatch.setenv("ANNUAL_LEAVE_SNAPSHOT", str(FIXTURE))
    token = client.post(
        "/api/auth/login",
        json={"username": "hr.demo", "password": "HrDemo@123456"},
    ).json()["access_token"]
    res = client.get(
        "/api/employees/annual-leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["employee_count"] == 2
    assert body["missing"] is False
    codes = {r["employee_code"] for r in body["employees"]}
    assert "5118" in codes
    rec = next(r for r in body["employees"] if r["employee_code"] == "5118")
    assert rec["curr_al"] == "9.33"
    assert rec["curr_remaining"] == "4.33"
    assert rec["used"] == "5"
    assert body["accrued_through_month"] == 7


def test_get_annual_leave_grid_missing_file(client, monkeypatch):
    monkeypatch.setenv("ANNUAL_LEAVE_SNAPSHOT", str(FIXTURE.parent / "khong_co.json"))
    token = client.post(
        "/api/auth/login",
        json={"username": "hr.demo", "password": "HrDemo@123456"},
    ).json()["access_token"]
    res = client.get(
        "/api/employees/annual-leave",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["missing"] is True
    assert res.json()["employee_count"] == 0
