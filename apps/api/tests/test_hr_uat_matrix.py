"""Ma trận UAT — user hr.demo (7 module, không Cấu Hình, không ai_query mặc định)."""

from __future__ import annotations

import pytest

HR_LOGIN = {"username": "hr.demo", "password": "HrDemo@123456"}


def _hr_headers(client):
    token = client.post("/api/auth/login", json=HR_LOGIN).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hr_user(client):
    return client.post("/api/auth/login", json=HR_LOGIN).json()["user"]


def test_hr_profile_and_modules(client):
    user = _hr_user(client)
    assert user["role_code"] == "hr_staff"
    assert "config" not in user["modules"]
    assert "hr" in user["modules"]
    assert len(user["modules"]) == 7
    assert "ai_query" not in user.get("permissions", [])


@pytest.mark.parametrize(
    "method,path,expect",
    [
        ("GET", "/api/portal/tabs", 200),
        ("GET", "/api/employees", 200),
        ("GET", "/api/departments", 200),
        ("GET", "/api/teams", 200),
        ("GET", "/api/labour-contracts", 200),
        ("GET", "/api/labour-contracts/expiring?within_days=60", 200),
        ("GET", "/api/employees/annual-leave", 200),
        ("GET", "/api/attendance/days?from=2025-10-01&to=2025-10-31", 200),
        ("GET", "/api/attendance/leave-types", 200),
        ("GET", "/api/attendance/leave-requests", 200),
        ("GET", "/api/payroll/payslips?period=2025-10", 200),
        ("GET", "/api/payroll/allowances/types", 200),
        ("GET", "/api/disputes", 200),
        ("GET", "/api/insurance/declarations?month=2025-10", 200),
        ("GET", "/api/reports/kpi?period=2025-10", 200),
        ("GET", "/api/reports/overview?period=2025-10", 200),
        ("GET", "/api/ai/todos", 200),
        ("GET", "/api/ai/alerts/mine", 200),
        ("GET", "/api/config/roles", 403),
        ("GET", "/api/users", 403),
        ("GET", "/api/ai/settings", 403),
        ("POST", "/api/ai/query", 403),
    ],
)
def test_hr_api_access_matrix(client, method: str, path: str, expect: int):
    headers = _hr_headers(client)
    if method == "GET":
        res = client.get(path, headers=headers)
    else:
        res = client.post(path, headers=headers, json={"message": "test"})
    assert res.status_code == expect, res.text[:300]


def test_hr_employee_crud_flow(client, db):
    from app.modules.mdm.models import Employee

    headers = _hr_headers(client)
    emps = client.get("/api/employees", headers=headers).json()
    assert len(emps) >= 1
    emp = next(e for e in emps if e["employee_code"] == "5290")
    detail = client.get(f"/api/employees/{emp['id']}", headers=headers)
    assert detail.status_code == 200

    validate = client.post(
        "/api/employees/validate",
        headers=headers,
        json={
            "is_new": False,
            "employee_id": emp["id"],
            "payload": {"full_name": emp["full_name"], "team_id": str(emp["team_id"])},
        },
    )
    assert validate.status_code == 200

    violations = client.get(f"/api/employees/{emp['id']}/violations", headers=headers)
    assert violations.status_code == 200


def test_hr_portal_config_not_allowed(client):
    """HR thấy metadata Cấu Hình nhưng allowed=false — Portal không cho vào."""
    body = client.get("/api/portal/tabs", headers=_hr_headers(client)).json()
    cfg = next(t for t in body["tabs"] if t["key"] == "config")
    assert cfg["allowed"] is False
    assert all(t["allowed"] for t in body["tabs"] if t["key"] != "config")


def test_hr_payroll_calculate_denied_or_allowed(client):
    """hr.demo có module payroll — được tính lương."""
    headers = _hr_headers(client)
    res = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert res.status_code in (200, 400, 409)
