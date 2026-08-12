"""P0 validation + P3 tái tuyển — kiểm thử API."""

from decimal import Decimal
from datetime import date
from uuid import UUID

from app.modules.mdm.models import Employee
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_resigned(client, headers, db, *, code: str, cccd: str | None = None):
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "Nguyễn Văn Test",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "pay_channel": "CASH",
            "join_date": "2020-01-15",
            "id_number": cccd,
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]
    emp_uuid = UUID(str(emp_id))

    if cccd:
        pc = db.query(PayComponent).filter(PayComponent.code == "TRANSPORT").first()
        emp = db.get(Employee, emp_uuid)
        db.add(
            EmployeeAllowanceAssignment(
                employee_id=emp.id,
                allowance_type_id=pc.id,
                amount=Decimal("760000"),
            )
        )
        db.commit()

    res = client.post(
        f"/api/employees/{emp_id}/resignations",
        headers=headers,
        json={
            "resign_type_code": "DPR",
            "last_working_date": "2025-06-30",
            "finalize": True,
        },
    )
    assert res.status_code == 201, res.text
    assert res.json().get("rehired_at") is None
    return str(emp_id), created.json()


def test_suggest_employee_code(client):
    headers = _hr_headers(client)
    res = client.get("/api/employees/suggest-code", headers=headers)
    assert res.status_code == 200
    assert res.json()["suggested_code"].isdigit()


def test_validate_rejects_bad_msnv_and_salary(client):
    headers = _hr_headers(client)
    res = client.post(
        "/api/employees/validate",
        headers=headers,
        json={
            "is_new": True,
            "payload": {
                "employee_code": "ABC",
                "full_name": "Một",
                "contract_salary": "0",
                "pay_channel": "CASH",
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    codes = {i["code"] for i in body["issues"]}
    assert "format" in codes
    assert "min" in codes


def test_create_rejects_zero_salary(client):
    headers = _hr_headers(client)
    res = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9010",
            "full_name": "Nguyễn Văn Mười",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "0",
            "pay_channel": "CASH",
        },
    )
    assert res.status_code == 400
    assert "Lương HĐ" in res.json()["detail"]


def test_validate_cccd_duplicate_resigned_suggests_rehire(client, db):
    headers = _hr_headers(client)
    cccd = "001234567890"
    _create_resigned(client, headers, db, code="9011", cccd=cccd)

    res = client.post(
        "/api/employees/validate",
        headers=headers,
        json={
            "is_new": True,
            "payload": {
                "employee_code": "9012",
                "full_name": "Nguyễn Văn Mới",
                "team_code": "T1",
                "department_code": "SW1",
                "contract_salary": "6000000",
                "id_number": cccd,
                "pay_channel": "CASH",
            },
        },
    )
    assert res.status_code == 200
    dup = next(i for i in res.json()["issues"] if i["code"] == "duplicate_resigned")
    assert dup["meta"]["employee_code"] == "9011"
    assert dup["meta"]["action"] == "rehire"


def test_rehire_fresh_start_resets_join_and_allowances(client, db):
    headers = _hr_headers(client)
    cccd = "001234567891"
    emp_id, _ = _create_resigned(client, headers, db, code="9013", cccd=cccd)
    before = db.get(Employee, UUID(emp_id))
    assert before.join_date == date(2020, 1, 15)
    assert (
        db.query(EmployeeAllowanceAssignment)
        .filter(EmployeeAllowanceAssignment.employee_id == UUID(emp_id))
        .count()
        >= 1
    )

    team = client.get("/api/teams", headers=headers).json()[0]
    res = client.post(
        f"/api/employees/{emp_id}/rehire",
        headers=headers,
        json={
            "rehire_date": "2026-01-10",
            "rehire_mode": "fresh_start",
            "team_id": team["id"],
            "status": "probation",
            "contract_salary": "6500000",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["rehire_mode"] == "fresh_start"
    emp = body["employee"]
    assert emp["status"] == "probation"
    assert emp["join_date"] == "2026-01-10"
    assert Decimal(str(emp["contract_salary"])) == Decimal("6500000")
    assert (
        db.query(EmployeeAllowanceAssignment)
        .filter(EmployeeAllowanceAssignment.employee_id == UUID(emp_id))
        .count()
        == 0
    )


def test_rehire_continuity_keeps_join_salary_allowances(client, db):
    headers = _hr_headers(client)
    cccd = "001234567892"
    emp_id, _ = _create_resigned(client, headers, db, code="9014", cccd=cccd)
    team = client.get("/api/teams", headers=headers).json()[0]

    res = client.post(
        f"/api/employees/{emp_id}/rehire",
        headers=headers,
        json={
            "rehire_date": "2026-02-01",
            "rehire_mode": "continuity",
            "rehire_reason": "Sếp SX giữ thâm niên",
            "team_id": team["id"],
            "status": "active",
        },
    )
    assert res.status_code == 200, res.text
    emp = res.json()["employee"]
    assert emp["join_date"] == "2020-01-15"
    assert Decimal(str(emp["contract_salary"])) == Decimal("6000000")
    assert (
        db.query(EmployeeAllowanceAssignment)
        .filter(EmployeeAllowanceAssignment.employee_id == UUID(emp_id))
        .count()
        >= 1
    )


def test_rehire_continuity_requires_reason(client, db):
    headers = _hr_headers(client)
    emp_id, _ = _create_resigned(client, headers, db, code="9015")
    team = client.get("/api/teams", headers=headers).json()[0]
    res = client.post(
        f"/api/employees/{emp_id}/rehire",
        headers=headers,
        json={
            "rehire_date": "2026-02-01",
            "rehire_mode": "continuity",
            "team_id": team["id"],
            "status": "active",
        },
    )
    assert res.status_code == 400
    assert "lý do" in res.json()["detail"].lower()


def test_rehire_legacy_resigned_without_resignation_record(client, db):
    """NV import «Đã nghỉ» chưa có employee_resignations — tái tuyển vẫn được."""
    headers = _hr_headers(client)
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": "9016",
            "full_name": "Legacy Nghỉ",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "7000000",
            "pay_channel": "CASH",
            "join_date": "2019-05-01",
            "status": "resigned",
            "resign_date": "2025-12-31",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]
    team = client.get("/api/teams", headers=headers).json()[0]

    res = client.post(
        f"/api/employees/{emp_id}/rehire",
        headers=headers,
        json={
            "rehire_date": "2026-03-01",
            "rehire_mode": "fresh_start",
            "team_id": team["id"],
            "status": "active",
            "contract_salary": "7500000",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["employee"]["status"] == "active"
