"""4.9 — HR payslip detail + chênh kỳ trước."""

from decimal import Decimal

from tests.test_oct2025_regression import apply_oct2025_fixture


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_payslip_list_includes_net_delta(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    assert client.post("/api/payroll/periods/2025-09/calculate", headers=headers).status_code == 200
    assert client.post("/api/payroll/periods/2025-10/calculate", headers=headers).status_code == 200

    slips = client.get("/api/payroll/payslips", headers=headers, params={"period": "2025-10"}).json()
    row5290 = next(s for s in slips if s["employee_code"] == "5290")
    assert row5290.get("prev_net") is not None
    assert row5290.get("net_delta") is not None
    assert Decimal(str(row5290["net_delta"])) == Decimal(str(row5290["net"])) - Decimal(
        str(row5290["prev_net"])
    )


def test_hr_payslip_detail_three_blocks(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    calc = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert calc.status_code == 200, calc.text
    slip = next(s for s in calc.json()["payslips"] if s["employee_code"] == "5290")

    detail = client.get(f"/api/payroll/payslips/{slip['id']}/detail", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["period"] == "2025-10"
    assert isinstance(body["work_lines"], list)
    assert isinstance(body["allowance_lines"], list)
    assert isinstance(body["deduction_lines"], list)
    assert body["annual_leave_remaining"] is not None
    assert float(body["payslip"]["net"]) == float(slip["net"])
