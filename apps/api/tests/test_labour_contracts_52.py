"""5.2 — labour_contracts CRUD + cảnh báo hết hạn 60 ngày."""

from datetime import date, timedelta
from uuid import UUID

from app.modules.mdm.models import Employee, LabourContract


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _sample_employee(db) -> Employee:
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    return emp


def test_labour_contract_crud(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)

    create = client.post(
        "/api/labour-contracts",
        headers=headers,
        json={
            "employee_id": str(emp.id),
            "contract_type_code": "HD1",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "base_salary": "8335000",
            "status": "active",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    contract_id = body["id"]
    assert body["contract_type_code"] == "HD1"
    assert body["seq_no"] == 1
    assert body["employee_code"] == "1514"
    assert body["contract_no"] == "1514/HĐ1"
    assert "HĐ lần 1" in body["times_label"]

    get_one = client.get(f"/api/labour-contracts/{contract_id}", headers=headers)
    assert get_one.status_code == 200
    assert get_one.json()["status"] == "active"

    listed = client.get(
        "/api/labour-contracts", headers=headers, params={"employee_id": str(emp.id)}
    )
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    updated = client.put(
        f"/api/labour-contracts/{contract_id}",
        headers=headers,
        json={"contract_type_code": "HD2", "base_salary": "8500000"},
    )
    assert updated.status_code == 200
    assert updated.json()["contract_type_code"] == "HD2"

    deleted = client.delete(f"/api/labour-contracts/{contract_id}", headers=headers)
    assert deleted.status_code == 200
    assert db.query(LabourContract).filter(LabourContract.id == UUID(contract_id)).count() == 0


def test_labour_contract_overlap_rejected(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)

    client.post(
        "/api/labour-contracts",
        headers=headers,
        json={
            "employee_id": str(emp.id),
            "contract_type_code": "TV",
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "status": "active",
        },
    )
    overlap = client.post(
        "/api/labour-contracts",
        headers=headers,
        json={
            "employee_id": str(emp.id),
            "contract_type_code": "HD1",
            "start_date": "2026-03-01",
            "end_date": "2027-03-01",
            "status": "active",
        },
    )
    assert overlap.status_code == 400
    assert "chồng lấn" in overlap.json()["detail"]


def test_expiring_contracts_within_60_days(client, db):
    headers = _hr_headers(client)
    emp = _sample_employee(db)
    today = date.today()
    soon_end = today + timedelta(days=30)
    far_start = today + timedelta(days=61)
    far_end = today + timedelta(days=400)

    client.post(
        "/api/labour-contracts",
        headers=headers,
        json={
            "employee_id": str(emp.id),
            "contract_type_code": "HD1",
            "start_date": (today - timedelta(days=300)).isoformat(),
            "end_date": soon_end.isoformat(),
            "status": "active",
        },
    )
    client.post(
        "/api/labour-contracts",
        headers=headers,
        json={
            "employee_id": str(emp.id),
            "contract_type_code": "HD1",
            "start_date": far_start.isoformat(),
            "end_date": far_end.isoformat(),
            "status": "active",
        },
    )

    expiring = client.get("/api/labour-contracts/expiring", headers=headers)
    assert expiring.status_code == 200
    rows = expiring.json()
    assert any(r["employee_code"] == "1514" for r in rows)
    assert all(r["days_until_expiry"] is not None and r["days_until_expiry"] <= 60 for r in rows)

    via_param = client.get(
        "/api/labour-contracts",
        headers=headers,
        params={"expiring_within_days": 60},
    )
    assert via_param.status_code == 200
    assert len(via_param.json()) >= 1


def test_labour_contract_renew_flow_tv_hd1_hd2(client, db):
    """GenusSuite: TV → HD1 → HD2, số HĐ MSNV/HĐ1."""
    headers = _hr_headers(client)
    emp = _sample_employee(db)
    emp_id = str(emp.id)

    # Dọn HĐ cũ của NV test (nếu có) để luồng sạch
    db.query(LabourContract).filter(LabourContract.employee_id == emp.id).delete()
    db.commit()

    tv = client.post(
        "/api/labour-contracts",
        headers=headers,
        json={
            "employee_id": emp_id,
            "contract_type_code": "TV",
            "start_date": "2025-06-01",
            "end_date": "2025-06-30",
            "base_salary": "5000000",
            "status": "active",
        },
    )
    assert tv.status_code == 201, tv.text

    preview = client.get(
        "/api/labour-contracts/renew-preview",
        headers=headers,
        params={"employee_id": emp_id},
    )
    assert preview.status_code == 200, preview.text
    pv = preview.json()
    assert pv["suggested_contract_type_code"] == "HD1"
    assert pv["suggested_contract_no"] == "1514/HĐ1"
    assert pv["suggested_start_date"] == "2025-07-01"

    hd1 = client.post(
        "/api/labour-contracts/renew",
        headers=headers,
        json={"employee_id": emp_id},
    )
    assert hd1.status_code == 201, hd1.text
    hd1_body = hd1.json()
    assert hd1_body["contract_type_code"] == "HD1"
    assert hd1_body["contract_no"] == "1514/HĐ1"
    assert hd1_body["times_label"] == "Lần 2 · HĐ lần 1"
    assert hd1_body["start_date"] == "2025-07-01"
    assert hd1_body["end_date"] == "2026-06-30"

    preview2 = client.get(
        "/api/labour-contracts/renew-preview",
        headers=headers,
        params={"employee_id": emp_id},
    )
    assert preview2.status_code == 200
    pv2 = preview2.json()
    assert pv2["suggested_contract_type_code"] == "HD2"
    assert "HD2" in pv2["allowed_contract_type_codes"]
    assert "VTH" in pv2["allowed_contract_type_codes"]

    hd2 = client.post(
        "/api/labour-contracts/renew",
        headers=headers,
        json={"employee_id": emp_id, "contract_type_code": "HD2"},
    )
    assert hd2.status_code == 201, hd2.text
    hd2_body = hd2.json()
    assert hd2_body["contract_type_code"] == "HD2"
    assert hd2_body["contract_no"] == "1514/HĐ2"
    assert "HĐ lần 2" in hd2_body["times_label"]

    listed = client.get(
        "/api/labour-contracts", headers=headers, params={"employee_id": emp_id}
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    emp_list = client.get("/api/employees", headers=headers, params={"q": "1514"})
    assert emp_list.status_code == 200
    row = next(r for r in emp_list.json() if r["employee_code"] == "1514")
    assert row["contract_type_label"] == "HĐ 1 năm — lần 2 (HD2)"
