"""5.4 — employee_resignations: 5 lý do, nhiều lần nghỉ, seq_no."""

from uuid import UUID

from app.modules.mdm.models import Employee, EmployeeResignation


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _sample_employee(db) -> Employee:
    return db.query(Employee).filter(Employee.employee_code == "5290").one()


RESIGN_TYPES = ("DPR", "AFL", "LWA", "CID", "DIS")


def test_resignation_reason_codes(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)

    for code in RESIGN_TYPES:
        res = client.post(
            f"/api/employees/{emp.id}/resignations",
            headers=headers,
            json={
                "resign_type_code": code,
                "last_working_date": "2024-06-30",
                "reason": f"Lý do {code}",
            },
        )
        assert res.status_code == 201, res.text
        assert res.json()["resign_type_code"] == code

    invalid = client.post(
        f"/api/employees/{emp.id}/resignations",
        headers=headers,
        json={"resign_type_code": "XYZ", "last_working_date": "2024-07-01"},
    )
    assert invalid.status_code == 422


def test_multiple_resignations_same_employee(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)

    first = client.post(
        f"/api/employees/{emp.id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "AFL",
            "last_working_date": "2023-12-31",
            "severance_months": 1,
            "severance_amount": "5000000",
        },
    )
    assert first.status_code == 201
    assert first.json()["seq_no"] == 1

    second = client.post(
        f"/api/employees/{emp.id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "CID",
            "last_working_date": "2025-08-31",
            "rehired_at": "2026-01-15",
        },
    )
    assert second.status_code == 201
    assert second.json()["seq_no"] == 2

    listed = client.get(f"/api/employees/{emp.id}/resignations", headers=headers)
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) >= 2
    seq_nos = sorted(r["seq_no"] for r in rows)
    assert seq_nos[0] == 1 and seq_nos[1] == 2

    count = db.query(EmployeeResignation).filter(EmployeeResignation.employee_id == emp.id).count()
    assert count >= 2


def test_resignation_update_and_delete(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)

    created = client.post(
        f"/api/employees/{emp.id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "DIS",
            "last_working_date": "2026-03-01",
            "handover_done": False,
        },
    )
    assert created.status_code == 201
    rid = created.json()["id"]

    updated = client.put(
        f"/api/employees/{emp.id}/resignations/{rid}",
        headers=headers,
        json={"handover_done": True, "severance_amount": "10000000"},
    )
    assert updated.status_code == 200
    assert updated.json()["handover_done"] is True

    deleted = client.delete(f"/api/employees/{emp.id}/resignations/{rid}", headers=headers)
    assert deleted.status_code == 200
    assert db.query(EmployeeResignation).filter(EmployeeResignation.id == UUID(rid)).count() == 0
