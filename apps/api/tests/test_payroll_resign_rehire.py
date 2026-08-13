"""Tái tuyển → nghỉ lại → không còn trong bảng lương kỳ sau ngày nghỉ."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from app.modules.payroll.period_eligibility import employee_on_payroll_period


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_active(client, headers, *, code: str) -> str:
    res = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": f"NV {code}",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "pay_channel": "CASH",
            "join_date": "2020-01-15",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_rehire_then_resign_excluded_from_next_payroll(client, db):
    """MSNV 1604/1718 pattern: tái tuyển, nghỉ lại — kỳ sau không còn phiếu âm."""
    headers = _hr_headers(client)
    code = "1604"
    emp_id = _create_active(client, headers, code=code)

    pay_jun = ensure_pay_period(db, "2026-06")
    rebuild_timesheets(db, "2026-06", recalc_days=False)
    calc1 = client.post("/api/payroll/periods/2026-06/calculate", headers=headers)
    assert calc1.status_code == 200, calc1.text
    assert any(p["employee_code"] == code for p in calc1.json()["payslips"])

    res = client.post(
        f"/api/employees/{emp_id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "DPR",
            "last_working_date": "2026-06-20",
            "finalize": True,
        },
    )
    assert res.status_code == 201, res.text

    team = client.get("/api/teams", headers=headers).json()[0]
    rehire = client.post(
        f"/api/employees/{emp_id}/rehire",
        headers=headers,
        json={
            "rehire_date": "2026-07-01",
            "rehire_mode": "fresh_start",
            "team_id": team["id"],
            "status": "active",
            "contract_salary": "6200000",
        },
    )
    assert rehire.status_code == 200, rehire.text

    pay_jul = ensure_pay_period(db, "2026-07")
    rebuild_timesheets(db, "2026-07", recalc_days=False)
    calc2 = client.post("/api/payroll/periods/2026-07/calculate", headers=headers)
    assert calc2.status_code == 200, calc2.text
    assert any(p["employee_code"] == code for p in calc2.json()["payslips"])

    res2 = client.post(
        f"/api/employees/{emp_id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "DPR",
            "last_working_date": "2026-07-15",
            "finalize": True,
        },
    )
    assert res2.status_code == 201, res2.text

    emp = db.query(Employee).filter(Employee.employee_code == code).one()
    assert emp.status == "resigned"
    assert emp.resign_date == date(2026, 7, 15)
    assert employee_on_payroll_period(emp, pay_jul.date_from, pay_jul.date_to)

    pay_aug = ensure_pay_period(db, "2026-08")
    rebuild_timesheets(db, "2026-08", recalc_days=False)
    assert not employee_on_payroll_period(emp, pay_aug.date_from, pay_aug.date_to)

    calc3 = client.post("/api/payroll/periods/2026-08/calculate", headers=headers)
    assert calc3.status_code == 200, calc3.text
    codes_aug = {p["employee_code"] for p in calc3.json()["payslips"]}
    assert code not in codes_aug

    listed = client.get("/api/payroll/payslips?period=2026-08", headers=headers)
    assert listed.status_code == 200
    assert code not in {p["employee_code"] for p in listed.json()}

    stale = (
        db.query(Payslip)
        .join(Employee, Employee.id == Payslip.employee_id)
        .filter(Payslip.pay_period_id == pay_aug.id, Employee.employee_code == code)
        .all()
    )
    assert stale == []


def test_resigned_before_period_not_recalculated_with_negative_net(client, db):
    """Phiếu nháp cũ của NV nghỉ trước kỳ bị xóa khi tính lại."""
    headers = _hr_headers(client)
    code = "1718"
    emp_id = _create_active(client, headers, code=code)
    emp_uuid = UUID(emp_id)

    pay = ensure_pay_period(db, "2026-08")
    rebuild_timesheets(db, "2026-08", recalc_days=False)

    calc = client.post("/api/payroll/periods/2026-08/calculate", headers=headers)
    assert calc.status_code == 200
    assert code in {p["employee_code"] for p in calc.json()["payslips"]}

    client.post(
        f"/api/employees/{emp_id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "DPR",
            "last_working_date": "2026-07-31",
            "finalize": True,
        },
    )

    emp = db.get(Employee, emp_uuid)
    assert not employee_on_payroll_period(emp, pay.date_from, pay.date_to)

    calc2 = client.post("/api/payroll/periods/2026-08/calculate", headers=headers)
    assert calc2.status_code == 200
    row = next((p for p in calc2.json()["payslips"] if p["employee_code"] == code), None)
    assert row is None

    listed = client.get("/api/payroll/payslips?period=2026-08", headers=headers)
    assert listed.status_code == 200
    assert code not in {p["employee_code"] for p in listed.json()}

    rebuild_timesheets(db, "2026-08", recalc_days=False)
    ts = client.get("/api/attendance/timesheets?period=2026-08", headers=headers)
    assert ts.status_code == 200
    assert code not in {r["employee_code"] for r in ts.json()}
