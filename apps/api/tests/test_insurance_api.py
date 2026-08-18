"""P6.2 — API Bảo Hiểm Thuế."""

from fastapi.testclient import TestClient


def _login(client: TestClient) -> dict[str, str]:
    r = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@DongJu2026"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_insurance_period_empty(client: TestClient):
    headers = _login(client)
    r = client.get("/api/insurance/periods/2099-01/summary", headers=headers)
    assert r.status_code == 404
    assert "Trợ Lý AI" in r.json()["detail"]


def test_si_base_from_old_payslip_lines():
    from decimal import Decimal

    from app.modules.insurance.service import si_base_from_payslip_lines

    old = {"si_base_used": "5200000.00", "si_base_raw": "5200000.00"}
    assert si_base_from_payslip_lines(old, Decimal("416000")) == Decimal("5200000.00")

    charged_zero = {"si_base_charged": "0", "si_base_used": "5200000.00"}
    assert si_base_from_payslip_lines(charged_zero, Decimal("0")) == Decimal("0")

    charged = {"si_base_charged": "6325000.00", "si_base_used": "6325000.00"}
    assert si_base_from_payslip_lines(charged, Decimal("506000")) == Decimal("6325000.00")

    assert si_base_from_payslip_lines({}, Decimal("416000")) == Decimal("0")
