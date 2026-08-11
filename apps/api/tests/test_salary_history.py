"""21§21.3 — employee_salary_history + lưới biến động HR."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.mdm.models import Employee, EmployeeSalaryHistory


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_update_employee_contract_salary_writes_history(client, db: Session):
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    old = emp.contract_salary or Decimal("0")
    new = old + Decimal("250000")

    headers = _hr_headers(client)
    res = client.put(
        f"/api/employees/{emp.id}",
        headers=headers,
        json={"contract_salary": str(new)},
    )
    assert res.status_code == 200, res.text

    db.expire_all()
    rows = (
        db.query(EmployeeSalaryHistory)
        .filter(
            EmployeeSalaryHistory.employee_id == emp.id,
            EmployeeSalaryHistory.field_code == "contract_salary",
        )
        .order_by(EmployeeSalaryHistory.created_at.desc())
        .all()
    )
    assert len(rows) >= 1
    latest = rows[0]
    assert latest.old_value == old
    assert latest.new_value == new


def test_bulk_salary_raise_writes_per_employee_history(client, db: Session):
    emp = db.query(Employee).filter(Employee.employee_code == "1643").one()
    old = emp.contract_salary or Decimal("0")
    bump = Decimal("100000")

    headers = _hr_headers(client)
    res = client.post(
        "/api/employees/salary-raise",
        headers=headers,
        json={
            "scope": "all",
            "target": "contract_salary",
            "amount": str(bump),
            "confirm": True,
            "confirm_again": True,
        },
    )
    assert res.status_code == 200, res.text

    db.expire_all()
    emp2 = db.query(Employee).filter(Employee.employee_code == "1643").one()
    assert emp2.contract_salary == old + bump

    row = (
        db.query(EmployeeSalaryHistory)
        .filter(
            EmployeeSalaryHistory.employee_id == emp.id,
            EmployeeSalaryHistory.field_code == "contract_salary",
        )
        .order_by(EmployeeSalaryHistory.created_at.desc())
        .first()
    )
    assert row is not None
    assert row.old_value == old
    assert row.new_value == old + bump
    assert row.approved_by is not None


def test_hr_movements_shows_salary_before_after(client, db: Session):
    emp = db.query(Employee).filter(Employee.employee_code == "5321").one()
    old = emp.contract_salary or Decimal("0")
    new = old + Decimal("50000")

    headers = _hr_headers(client)
    patch = client.put(
        f"/api/employees/{emp.id}",
        headers=headers,
        json={"contract_salary": str(new)},
    )
    assert patch.status_code == 200, patch.text

    res = client.get(f"/api/hr/movements?employee_id={emp.id}", headers=headers)
    assert res.status_code == 200, res.text
    rows = [r for r in res.json() if r["movement_type"] == "salary"]
    assert len(rows) >= 1
    hit = rows[0]
    assert hit["value_before"] is not None
    assert hit["value_after"] is not None
    assert hit["employee_code"] == "5321"


def test_list_employee_salary_history_api(client, db: Session):
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    headers = _hr_headers(client)
    res = client.get(f"/api/employees/{emp.id}/salary-history", headers=headers)
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)
