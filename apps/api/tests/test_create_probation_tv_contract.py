"""NV mới thử việc — tự tạo HĐ TV."""

from datetime import date
from decimal import Decimal

from uuid import UUID

from app.modules.mdm.models import Department, Employee, LabourContract, Team


def test_create_probation_employee_gets_tv_contract(client, db):
    dept = Department(code="TV1", name="TV Dept", category="direct")
    db.add(dept)
    db.flush()
    team = Team(
        department_id=dept.id,
        code="TV1-1",
        name="TV Team",
        effective_from=date(2026, 1, 1),
    )
    db.add(team)
    db.flush()

    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9901",
            "full_name": "NV THU VIEC MOI",
            "team_id": str(team.id),
            "join_date": "2026-08-01",
            "probation_salary": "7000000",
            "contract_salary": "8335000",
            "status": "probation",
        },
    )
    assert res.status_code == 201, res.text
    emp_id = res.json()["id"]

    lc = db.query(LabourContract).filter(LabourContract.employee_id == UUID(emp_id)).one()
    assert lc.contract_type_code == "TV"
    assert lc.status == "active"
    assert lc.end_date is not None
