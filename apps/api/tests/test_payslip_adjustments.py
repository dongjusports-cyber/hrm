"""10.3#15 — payslip_adjustments (addon → gross, deduction → net)."""

from decimal import Decimal

from tests.test_oct2025_regression import apply_oct2025_fixture


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_addon_and_deduction_in_calculate(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)

    # baseline
    base = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert base.status_code == 200, base.text
    slip0 = next(s for s in base.json()["payslips"] if s["employee_code"] == "5290")
    net0 = Decimal(str(slip0["net"]))
    gross0 = Decimal(str(slip0["gross"]))

    addon = client.post(
        "/api/payroll/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "5290",
            "kind": "addon",
            "reason": "Truy lĩnh T9",
            "amount": "100000",
        },
    )
    assert addon.status_code == 200, addon.text

    deduct = client.post(
        "/api/payroll/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "5290",
            "kind": "deduction",
            "reason": "Tạm ứng",
            "amount": "50000",
        },
    )
    assert deduct.status_code == 200, deduct.text

    again = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert again.status_code == 200
    slip = next(s for s in again.json()["payslips"] if s["employee_code"] == "5290")
    assert Decimal(str(slip["other_adjustments"])) == Decimal("100000")
    assert Decimal(str(slip["other_deductions"])) == Decimal("50000")
    assert Decimal(str(slip["gross"])) == gross0 + Decimal("100000")
    assert Decimal(str(slip["net"])) == net0 + Decimal("100000") - Decimal("50000")


def test_block_adjust_when_published(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    assert client.post("/api/payroll/periods/2025-10/calculate", headers=headers).status_code == 200
    assert client.post("/api/payroll/periods/2025-10/publish", headers=headers).status_code == 200

    r = client.post(
        "/api/payroll/adjustments",
        headers=headers,
        json={
            "period": "2025-10",
            "employee_code": "5290",
            "kind": "addon",
            "reason": "Muộn",
            "amount": "1000",
        },
    )
    assert r.status_code == 400
    assert "Trợ Lý AI" in r.json()["detail"]
