"""2.8 — Admin danh mục CRUD."""


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


def test_admin_create_leave_type_visible_in_timekeeping(client):
    headers = _admin_headers(client)
    res = client.post(
        "/api/config/catalog/leave-types",
        headers=headers,
        json={
            "code": "TST",
            "name": "Nghỉ thử Admin 2.8",
            "paid_by_company": True,
            "pay_ratio_percent": 100,
            "counts_as_worked_day": True,
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["code"] == "TST"

    hr = _hr_headers(client)
    listed = client.get("/api/attendance/leave-types", headers=hr)
    assert listed.status_code == 200
    codes = {x["code"] for x in listed.json()}
    assert "TST" in codes


def test_hr_cannot_create_leave_type(client):
    res = client.post(
        "/api/config/catalog/leave-types",
        headers=_hr_headers(client),
        json={"code": "X", "name": "x"},
    )
    assert res.status_code == 403


def test_admin_list_pay_components(client):
    headers = _admin_headers(client)
    res = client.get("/api/config/catalog/pay-components", headers=headers)
    assert res.status_code == 200
    codes = {x["code"] for x in res.json()}
    assert "ATTEND" in codes


def test_admin_create_lookup(client):
    headers = _admin_headers(client)
    res = client.post(
        "/api/config/catalog/lookup-values",
        headers=headers,
        json={
            "group_code": "ethnicity",
            "code": "TST_ETH",
            "name": "Dân tộc thử",
            "sort_order": 999,
        },
    )
    assert res.status_code == 201, res.text
    listed = client.get(
        "/api/config/catalog/lookup-values?group_code=ethnicity", headers=headers
    )
    assert any(x["code"] == "TST_ETH" for x in listed.json())
