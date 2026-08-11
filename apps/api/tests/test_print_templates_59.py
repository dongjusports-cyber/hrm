"""5.9 — print templates return HTML (GenusSuite mẫu)."""

from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_print_templates_html(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()

    contract = client.get(f"/api/print/employees/{emp.id}/contract", headers=headers)
    assert contract.status_code == 200
    assert "text/html" in contract.headers["content-type"]
    assert "1514" in contract.text
    assert "HỢP ĐỒNG LAO ĐỘNG" in contract.text
    assert "DONGJU SPORTS" in contract.text
    assert "KIM JEONGTAG" in contract.text

    probation = client.get(f"/api/print/employees/{emp.id}/probation", headers=headers)
    assert probation.status_code == 200
    assert "THỎA THUẬN THỬ VIỆC" in probation.text
    assert emp.full_name in probation.text

    decision = client.get(f"/api/print/employees/{emp.id}/decision", headers=headers)
    assert decision.status_code == 200
    assert "Quyết định" in decision.text
