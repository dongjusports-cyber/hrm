"""5.1 — employee_educations / experiences / health_checks CRUD."""

from datetime import date

from app.modules.mdm.models import Employee, EmployeeEducation, EmployeeExperience, EmployeeHealthCheck


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _emp(client, db) -> Employee:
    from app.modules.mdm.models import Team

    team = db.query(Team).first()
    assert team is not None
    headers = _hr_headers(client)
    res = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "99100",
            "full_name": "Subrecord Test",
            "team_id": str(team.id),
            "contract_salary": "8000000",
        },
    )
    assert res.status_code == 201, res.text
    return db.query(Employee).filter(Employee.employee_code == "99100").one()


def test_education_experience_health_crud(client, db):
    headers = _hr_headers(client)
    emp = _emp(client, db)

    edu = client.post(
        f"/api/employees/{emp.id}/educations",
        headers=headers,
        json={
            "from_date": "2010-09-01",
            "to_date": "2014-06-30",
            "school_name": "ĐH Bách Khoa",
            "major": "Cơ khí",
            "degree_code": "DH",
        },
    )
    assert edu.status_code == 201, edu.text
    edu_id = edu.json()["id"]

    exp = client.post(
        f"/api/employees/{emp.id}/experiences",
        headers=headers,
        json={
            "from_date": "2015-01-01",
            "to_date": "2018-12-31",
            "company_name": "Cty ABC",
            "position_title": "Công nhân",
        },
    )
    assert exp.status_code == 201, exp.text
    exp_id = exp.json()["id"]

    hc = client.post(
        f"/api/employees/{emp.id}/health-checks",
        headers=headers,
        json={
            "check_date": "2026-01-15",
            "facility_name": "BV Lao động",
            "result_summary": "Đạt",
        },
    )
    assert hc.status_code == 201, hc.text
    hc_id = hc.json()["id"]

    listed = client.get(f"/api/employees/{emp.id}/educations", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/api/employees/{emp.id}/educations/{edu_id}",
        headers=headers,
        json={"school_name": "ĐH Bách Khoa TP.HCM"},
    )
    assert updated.status_code == 200
    assert updated.json()["school_name"] == "ĐH Bách Khoa TP.HCM"

    assert client.delete(f"/api/employees/{emp.id}/experiences/{exp_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/employees/{emp.id}/health-checks/{hc_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/employees/{emp.id}/educations/{edu_id}", headers=headers).status_code == 200

    assert db.query(EmployeeEducation).filter(EmployeeEducation.employee_id == emp.id).count() == 0
    assert db.query(EmployeeExperience).filter(EmployeeExperience.employee_id == emp.id).count() == 0
    assert db.query(EmployeeHealthCheck).filter(EmployeeHealthCheck.employee_id == emp.id).count() == 0
