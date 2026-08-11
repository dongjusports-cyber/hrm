"""5.1 — cột hồ sơ employees + API."""

from datetime import date

from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_employee_with_profile_fields(client, db):
    headers = _hr_headers(client)
    from app.modules.mdm.models import Team

    team = db.query(Team).first()
    assert team is not None

    res = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "99001",
            "full_name": "Nguyễn Test 5.1",
            "team_id": str(team.id),
            "contract_salary": "8500000",
            "probation_salary": "7000000",
            "pay_channel": "ATM",
            "status": "probation",
            "join_date": "2026-08-01",
            "birth_date": "1995-03-15",
            "nationality_code": "VN",
            "si_book_no": "BH99001",
            "phone": "0901234567",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["employee_code"] == "99001"
    assert body["birth_date"] == "1995-03-15"
    assert body["si_book_no"] == "BH99001"

    emp = db.query(Employee).filter(Employee.employee_code == "99001").one()
    assert emp.birth_date == date(1995, 3, 15)
    assert emp.si_book_no == "BH99001"


def test_update_employee_profile_fields(client, db):
    headers = _hr_headers(client)
    from app.modules.mdm.models import Team

    team = db.query(Team).first()
    assert team is not None
    client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "99002",
            "full_name": "Nguyễn Update 5.1",
            "team_id": str(team.id),
            "contract_salary": "8000000",
        },
    )
    emp = db.query(Employee).filter(Employee.employee_code == "99002").one()

    res = client.put(
        f"/api/employees/{emp.id}",
        headers=headers,
        json={
            "permanent_address": "123 Đường A, Q.1, TP.HCM",
            "marital_status": "married",
            "children_count": 2,
            "education_code": "TH12",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["permanent_address"] == "123 Đường A, Q.1, TP.HCM"
    assert body["marital_status"] == "married"
    assert body["children_count"] == 2
    assert body["education_code"] == "TH12"
