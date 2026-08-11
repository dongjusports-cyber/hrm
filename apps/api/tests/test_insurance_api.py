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
