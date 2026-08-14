"""Lọc NV theo trạng thái suy ra — thử việc / thai sản."""

from datetime import date, timedelta


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_probation_filter_by_unsigned_contract(client):
    """NV active nhưng chưa ký HĐ chính thức → tab Thử việc."""
    headers = _hr_headers(client)
    code = "9101"
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "NV Thử Việc Filter",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": date.today().isoformat(),
            "contract_signed_at": None,
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]
    assert created.json()["effective_status"] == "probation"

    listed = client.get("/api/employees?status=probation", headers=headers).json()
    codes = {e["employee_code"] for e in listed}
    assert code in codes

    active_list = client.get("/api/employees?status=active", headers=headers).json()
    assert code not in {e["employee_code"] for e in active_list}

    # Tìm MSNV trên tab Chính thức vẫn thấy NV (đang thuộc tab Thử việc)
    search_active = client.get(f"/api/employees?status=active&q={code}", headers=headers).json()
    assert code in {e["employee_code"] for e in search_active}
    assert search_active[0]["effective_status"] == "probation"

    future = (date.today() + timedelta(days=30)).isoformat()
    client.put(
        f"/api/employees/{emp_id}",
        headers=headers,
        json={"contract_signed_at": future},
    )
    detail = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    assert detail["effective_status"] == "probation"


def test_maternity_filter_by_status(client):
    """NV status=maternity xuất hiện ở tab Thai sản, không ở Chính thức."""
    headers = _hr_headers(client)
    code = "9102"
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": "NV Thai San Filter",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "status": "maternity",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["effective_status"] == "maternity"

    mat_list = client.get("/api/employees?status=maternity", headers=headers).json()
    assert code in {e["employee_code"] for e in mat_list}

    active_list = client.get("/api/employees?status=active", headers=headers).json()
    assert code not in {e["employee_code"] for e in active_list}
