"""2.7 — roles + role_permissions, quyền hiệu lực từ vai trò."""

from app.modules.config.portal_tabs import MODULE_KEYS


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_seed_roles_and_hr_demo_from_role(client):
    res = client.get("/api/config/roles", headers=_admin_headers(client))
    assert res.status_code == 200
    codes = {r["code"] for r in res.json()["roles"]}
    assert {"admin", "hr_staff", "payroll_accountant"} <= codes

    login = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["user"]
    assert login.get("role_code") == "hr_staff"
    assert "config" not in login["modules"]
    assert len(login["modules"]) == 7


def test_payroll_accountant_only_sees_payroll_module(client):
    headers = _admin_headers(client)
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "kt.luong.demo",
            "full_name": "Kế Toán Lương Demo",
            "password": "KtLuong@123456",
            "modules": [],
            "permissions": [],
            "role_code": "payroll_accountant",
            "must_change_password": False,
        },
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/api/auth/login",
        json={"username": "kt.luong.demo", "password": "KtLuong@123456"},
    ).json()["user"]
    assert login["modules"] == ["payroll"]

    token = client.post(
        "/api/auth/login",
        json={"username": "kt.luong.demo", "password": "KtLuong@123456"},
    ).json()["access_token"]
    tabs = client.get("/api/portal/tabs", headers={"Authorization": f"Bearer {token}"}).json()[
        "tabs"
    ]
    allowed = [t["key"] for t in tabs if t["allowed"]]
    assert allowed == ["payroll"]


def test_update_role_matrix_changes_effective_access(client):
    headers = _admin_headers(client)
    matrix = client.get("/api/config/roles/payroll_accountant", headers=headers).json()
    assert matrix["modules"][3]["module_key"] == "payroll"
    assert matrix["modules"][3]["level"] == "view"

    # Thêm quyền xem HR (chỉ test API ma trận)
    modules = []
    for m in matrix["modules"]:
        row = dict(m)
        if row["module_key"] == "hr":
            row["level"] = "view"
        modules.append(row)
    put = client.put(
        "/api/config/roles/payroll_accountant",
        headers=headers,
        json={"modules": modules},
    )
    assert put.status_code == 200
    hr_level = next(x for x in put.json()["modules"] if x["module_key"] == "hr")["level"]
    assert hr_level == "view"

    # Khôi phục chỉ payroll
    restore = []
    for m in put.json()["modules"]:
        row = dict(m)
        if row["module_key"] != "payroll":
            row["level"] = "none"
        restore.append(row)
    client.put("/api/config/roles/payroll_accountant", headers=headers, json={"modules": restore})


def test_hr_cannot_list_roles(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    res = client.get("/api/config/roles", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_role_matrix_covers_all_modules(client):
    headers = _admin_headers(client)
    body = client.get("/api/config/roles/hr_staff", headers=headers).json()
    keys = {m["module_key"] for m in body["modules"]}
    assert keys == set(MODULE_KEYS)
