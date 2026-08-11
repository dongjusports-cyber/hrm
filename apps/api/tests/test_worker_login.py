"""P1.5 — Worker login stub (MSNV + JWT audience worker)."""

from app.modules.worker.service import DEFAULT_WORKER_PASSWORD


def test_worker_login_ok(client):
    res = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": DEFAULT_WORKER_PASSWORD},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["worker"]["employee_code"] == "5290"
    assert body["worker"]["must_change_password"] is True
    assert body["access_token"]


def test_worker_token_cannot_access_staff_portal(client):
    token = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": DEFAULT_WORKER_PASSWORD},
    ).json()["access_token"]
    res = client.get("/api/portal/tabs", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_staff_token_cannot_access_worker_me(client):
    token = client.post(
        "/api/auth/login",
        json={"username": "hr.demo", "password": "HrDemo@123456"},
    ).json()["access_token"]
    res = client.get("/api/worker/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_worker_payslips_empty_when_not_published(client):
    token = client.post(
        "/api/worker/login",
        json={"employee_code": "1514", "password": DEFAULT_WORKER_PASSWORD},
    ).json()["access_token"]
    res = client.get("/api/worker/payslips", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == []


def test_worker_wrong_password(client):
    res = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": "sai"},
    )
    assert res.status_code == 401
    assert "còn 2 lần thử" in res.json()["detail"]


def test_worker_change_password(client):
    login = client.post(
        "/api/worker/login",
        json={"employee_code": "1732", "password": DEFAULT_WORKER_PASSWORD},
    )
    token = login.json()["access_token"]
    res = client.post(
        "/api/worker/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": DEFAULT_WORKER_PASSWORD, "new_password": "NewPass@12345"},
    )
    assert res.status_code == 200
    again = client.post(
        "/api/worker/login",
        json={"employee_code": "1732", "password": "NewPass@12345"},
    )
    assert again.status_code == 200
    assert again.json()["worker"]["must_change_password"] is False
