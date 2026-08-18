"""P0.4 — login, RBAC, portal tabs allowed, thông báo tiếng Việt."""


def test_login_admin_full_modules(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["user"]["role"] == "admin"
    assert "refresh_token" not in body
    assert body["access_token"]
    assert len(body["user"]["modules"]) == 8
    assert "config" in body["user"]["modules"]
    assert "ai_query" in body["user"]["permissions"]


def test_login_hr_demo_no_config(client):
    res = client.post("/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"})
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["role"] == "user"
    assert "config" not in user["modules"]
    assert len(user["modules"]) == 7


def test_portal_tabs_allowed_flags(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    res = client.get("/api/portal/tabs", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    tabs = res.json()["tabs"]
    assert len(tabs) == 8
    by_key = {t["key"]: t for t in tabs}
    assert by_key["config"]["allowed"] is False
    assert by_key["hr"]["allowed"] is True
    assert all("name" in t for t in tabs)


def test_me_and_vietnamese_errors(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert "Nguyễn Thị HR" in me.json()["full_name"]

    bad = client.post("/api/auth/login", json={"username": "admin", "password": "sai"})
    assert bad.status_code == 401
    assert "còn 2 lần thử" in bad.json()["detail"]


def test_unauthenticated_tabs(client):
    res = client.get("/api/portal/tabs")
    assert res.status_code == 401
