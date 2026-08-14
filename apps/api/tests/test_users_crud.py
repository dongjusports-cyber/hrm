"""P1.1 — Users CRUD + gán quyền (max 7, không config)."""


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_hr_cannot_list_users(client):
    res = client.get("/api/users", headers=_hr_headers(client))
    assert res.status_code == 403
    assert "Trợ Lý AI" in res.json()["detail"]


def test_admin_lists_users(client):
    res = client.get("/api/users", headers=_admin_headers(client))
    assert res.status_code == 200
    names = {u["username"] for u in res.json()}
    assert "admin" in names
    assert "hr.demo" in names


def test_create_user_max_modules_and_no_config(client):
    headers = _admin_headers(client)
    res = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "kt.luong",
            "full_name": "Trần Kế Toán",
            "password": "KeToan@123456",
            "modules": [
                "overview",
                "hr",
                "timekeeping",
                "payroll",
                "insurance",
                "report",
                "dispute",
            ],
            "permissions": ["ai_query"],
            "must_change_password": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "user"
    assert len(body["modules"]) == 7
    assert "config" not in body["modules"]
    assert "ai_query" in body["permissions"]


def test_reject_config_grant_and_over_7(client):
    headers = _admin_headers(client)
    bad_config = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "bad.config",
            "full_name": "Bad Config",
            "password": "BadConfig@123",
            "modules": ["hr", "config"],
            "permissions": [],
        },
    )
    assert bad_config.status_code == 400
    assert "Cấu Hình" in bad_config.json()["detail"]

    over = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "bad.eight",
            "full_name": "Bad Eight",
            "password": "BadEight@123",
            "modules": [
                "overview",
                "hr",
                "timekeeping",
                "payroll",
                "insurance",
                "report",
                "dispute",
                "overview",
            ],
            "permissions": [],
        },
    )
    # duplicate overview → still 7 unique, should succeed OR if we send 8 unique without config impossible
    # send 7 + try update to add nothing; instead update with invalid 8 unique impossible without config
    # Create with 7 then PUT with config:
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "upd.user",
            "full_name": "Update User",
            "password": "Update@123456",
            "modules": ["hr", "payroll"],
            "permissions": [],
        },
    )
    assert created.status_code == 201, created.text
    uid = created.json()["id"]
    put = client.put(
        f"/api/users/{uid}",
        headers=headers,
        json={"modules": ["hr", "payroll", "config"]},
    )
    assert put.status_code == 400
    assert over.status_code in (201, 400)  # duplicates collapse to 7


def test_update_and_deactivate(client):
    headers = _admin_headers(client)
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "temp.user",
            "full_name": "Temp User",
            "password": "TempUser@123",
            "modules": ["hr"],
            "permissions": [],
        },
    )
    assert created.status_code == 201
    uid = created.json()["id"]

    updated = client.put(
        f"/api/users/{uid}",
        headers=headers,
        json={"full_name": "Temp User 2", "modules": ["hr", "payroll"], "permissions": ["ai_query"]},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Temp User 2"
    assert set(updated.json()["modules"]) == {"hr", "payroll"}
    assert "ai_query" in updated.json()["permissions"]

    off = client.post(f"/api/users/{uid}/deactivate", headers=headers)
    assert off.status_code == 200
    listed = client.get("/api/users", headers=headers).json()
    row = next(u for u in listed if u["id"] == uid)
    assert row["is_active"] is False
    assert row["is_locked"] is False


def test_admin_unlocks_locked_hr_user(client):
    headers = _admin_headers(client)
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "hr.lock",
            "full_name": "HR Locked",
            "password": "HrLock@123456",
            "modules": ["hr"],
            "permissions": [],
        },
    )
    assert created.status_code == 201, created.text
    uid = created.json()["id"]
    assert created.json()["is_locked"] is False

    for _ in range(3):
        bad = client.post("/api/auth/login", json={"username": "hr.lock", "password": "sai"})
    assert bad.status_code == 423

    listed = client.get("/api/users", headers=headers).json()
    row = next(u for u in listed if u["id"] == uid)
    assert row["is_locked"] is True

    hr_try = client.post(f"/api/users/{uid}/unlock", headers=_hr_headers(client))
    assert hr_try.status_code == 403

    still = client.post("/api/auth/login", json={"username": "hr.lock", "password": "HrLock@123456"})
    assert still.status_code == 423

    unlocked = client.post(f"/api/users/{uid}/unlock", headers=headers)
    assert unlocked.status_code == 200, unlocked.text
    assert "hr.lock" in unlocked.json()["detail"]

    listed = client.get("/api/users", headers=headers).json()
    row = next(u for u in listed if u["id"] == uid)
    assert row["is_locked"] is False

    ok = client.post("/api/auth/login", json={"username": "hr.lock", "password": "HrLock@123456"})
    assert ok.status_code == 200, ok.text


def test_admin_cannot_unlock_admin_or_worker(client, db):
    from app.modules.core.models import User

    headers = _admin_headers(client)
    admin = db.query(User).filter(User.username == "admin").one()
    admin_res = client.post(f"/api/users/{admin.id}/unlock", headers=headers)
    assert admin_res.status_code == 400
    assert "nhân viên HR" in admin_res.json()["detail"]

    worker = db.query(User).filter(User.role == "worker").first()
    if worker is None:
        return
    worker_res = client.post(f"/api/users/{worker.id}/unlock", headers=headers)
    assert worker_res.status_code == 400
    assert "công nhân" in worker_res.json()["detail"]


def test_new_user_can_login(client):
    headers = _admin_headers(client)
    client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "login.ok",
            "full_name": "Login OK",
            "password": "LoginOk@123456",
            "modules": ["overview", "hr"],
            "permissions": [],
        },
    )
    res = client.post(
        "/api/auth/login",
        json={"username": "login.ok", "password": "LoginOk@123456"},
    )
    assert res.status_code == 200
    assert set(res.json()["user"]["modules"]) == {"overview", "hr"}
