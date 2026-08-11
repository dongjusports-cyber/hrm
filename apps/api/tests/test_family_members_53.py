"""5.3 — employee_family_members CRUD + tính người phụ thuộc hiệu lực."""

from datetime import date
from uuid import UUID

from app.modules.mdm.models import Employee, EmployeeFamilyMember


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _sample_employee(db) -> Employee:
    return db.query(Employee).filter(Employee.employee_code == "1643").one()


def test_family_member_crud(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)

    create = client.post(
        f"/api/employees/{emp.id}/family-members",
        headers=headers,
        json={
            "relationship_code": "cha",
            "full_name": "Nguyễn Văn Cha",
            "birth_date": "1965-01-01",
            "is_tax_dependent": False,
        },
    )
    assert create.status_code == 201, create.text
    member_id = create.json()["id"]
    assert create.json()["relationship_code"] == "cha"

    listed = client.get(f"/api/employees/{emp.id}/family-members", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    updated = client.put(
        f"/api/employees/{emp.id}/family-members/{member_id}",
        headers=headers,
        json={"full_name": "Nguyễn Văn Cha (cập nhật)"},
    )
    assert updated.status_code == 200
    assert "cập nhật" in updated.json()["full_name"]

    deleted = client.delete(
        f"/api/employees/{emp.id}/family-members/{member_id}", headers=headers
    )
    assert deleted.status_code == 200
    assert (
        db.query(EmployeeFamilyMember).filter(EmployeeFamilyMember.id == UUID(member_id)).count() == 0
    )


def test_compute_effective_tax_dependents(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)
    today = date.today()
    child_birth = date(today.year - 10, 6, 1).isoformat()
    expired_from = "2020-01-01"
    expired_to = "2024-12-31"
    active_from = "2025-01-01"

    for payload in (
        {
            "relationship_code": "con",
            "full_name": "Con một",
            "birth_date": child_birth,
            "is_tax_dependent": True,
            "dependent_from": active_from,
        },
        {
            "relationship_code": "con",
            "full_name": "Con hai",
            "birth_date": child_birth,
            "is_tax_dependent": True,
            "dependent_from": active_from,
        },
        {
            "relationship_code": "me",
            "full_name": "Mẹ (hết hiệu lực)",
            "is_tax_dependent": True,
            "dependent_from": expired_from,
            "dependent_to": expired_to,
        },
        {
            "relationship_code": "anh",
            "full_name": "Anh (không đăng ký GT)",
            "is_tax_dependent": False,
            "dependent_from": active_from,
        },
    ):
        res = client.post(
            f"/api/employees/{emp.id}/family-members",
            headers=headers,
            json=payload,
        )
        assert res.status_code == 201, res.text

    tax = client.get(f"/api/employees/{emp.id}/tax-dependents", headers=headers)
    assert tax.status_code == 200
    body = tax.json()
    assert body["effective_count"] == 2
    assert len(body["members"]) == 2
    assert all(m["is_effective"] for m in body["members"])

    past = client.get(
        f"/api/employees/{emp.id}/tax-dependents",
        headers=headers,
        params={"as_of": "2023-06-01"},
    )
    assert past.status_code == 200
    assert past.json()["effective_count"] == 1
