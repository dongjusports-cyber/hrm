"""In phụ lục tăng lương — PHU LUC TANG LUONG."""

from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_print_salary_raise_appendix(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()

    res = client.post(
        "/api/print/salary-raise",
        headers=headers,
        json={
            "scope": "employees",
            "employee_ids": [str(emp.id)],
            "target": "contract_salary",
            "amount": "300000",
        },
    )
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "PHỤ LỤC HỢP ĐỒNG LAO ĐỘNG" in res.text
    assert emp.full_name in res.text
    assert "KIM JEONGTAG" in res.text
    assert "DONGJU SPORTS" in res.text


def test_salary_raise_employees_scope(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    old = emp.contract_salary

    preview = client.post(
        "/api/employees/salary-raise/preview",
        headers=headers,
        json={
            "scope": "employees",
            "employee_ids": [str(emp.id)],
            "target": "contract_salary",
            "amount": "100000",
        },
    )
    assert preview.status_code == 200
    assert preview.json()["affected_count"] == 1

    # không lưu thật — chỉ kiểm tra phạm vi employees
    db.refresh(emp)
    assert emp.contract_salary == old
