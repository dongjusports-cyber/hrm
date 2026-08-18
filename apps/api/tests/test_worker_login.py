"""P1.5 — Worker login stub (MSNV + JWT audience worker)."""

from tests.worker_auth import default_login_password, unlocked_worker_headers


def test_worker_login_ok(client):
    res = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": default_login_password("5290")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["worker"]["employee_code"] == "5290"
    assert body["worker"]["must_change_password"] is True
    assert body["access_token"]
    assert "refresh_token" not in body


def test_worker_token_cannot_access_staff_portal(client):
    token = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": default_login_password("5290")},
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
    res = client.get("/api/worker/payslips", headers=unlocked_worker_headers(client, "1514"))
    assert res.status_code == 200
    assert res.json() == []


def test_worker_must_change_password_blocks_payslips(client):
    """QA-03: mật khẩu mặc định — API phiếu lương 403, /me vẫn được."""
    token = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": default_login_password("5290")},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/worker/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True
    blocked = client.get("/api/worker/payslips", headers=headers)
    assert blocked.status_code == 403
    assert "đổi mật khẩu" in blocked.json()["detail"]


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
        json={"employee_code": "1732", "password": default_login_password("1732")},
    )
    token = login.json()["access_token"]
    res = client.post(
        "/api/worker/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": default_login_password("1732"), "new_password": "NewPass@12345"},
    )
    assert res.status_code == 200
    again = client.post(
        "/api/worker/login",
        json={"employee_code": "1732", "password": "NewPass@12345"},
    )
    assert again.status_code == 200
    assert again.json()["worker"]["must_change_password"] is False
