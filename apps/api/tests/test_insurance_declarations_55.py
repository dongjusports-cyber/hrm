"""5.5 — insurance_declarations propose / export / mark submitted."""

from datetime import date
from uuid import UUID

from app.modules.insurance.models import InsuranceDeclaration
from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_propose_increase_for_new_joiner(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    today = date.today()
    emp.join_date = today.replace(day=1)
    emp.si_enrolled = True
    emp.contract_salary = 8335000
    db.commit()

    res = client.post(
        f"/api/insurance/declarations/propose/{today.year:04d}-{today.month:02d}",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created_count"] >= 1
    assert body["by_type"]["increase"] >= 1
    assert any(x["employee_code"] == "1514" for x in body["items"])


def test_export_and_mark_submitted(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    month = f"{date.today().year:04d}-{date.today().month:02d}"
    row = InsuranceDeclaration(
        employee_id=emp.id,
        declaration_type="increase",
        effective_month=month,
        old_salary=0,
        new_salary=8335000,
        reason_code="join",
        status="draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    dl = client.get(
        "/api/insurance/declarations/export/download",
        headers=headers,
        params={"effective_month": month},
    )
    assert dl.status_code == 200
    assert "employee_code" in dl.text
    assert "1514" in dl.text

    updated = db.query(InsuranceDeclaration).filter(InsuranceDeclaration.id == row.id).one()
    assert updated.status == "exported"
    assert updated.batch_no

    mark = client.post(
        "/api/insurance/declarations/mark-submitted",
        headers=headers,
        json={"batch_no": updated.batch_no},
    )
    assert mark.status_code == 200
    assert mark.json()["marked"] >= 1

    final = db.query(InsuranceDeclaration).filter(InsuranceDeclaration.id == UUID(str(row.id))).one()
    assert final.status == "submitted"
    assert final.submitted_at is not None
