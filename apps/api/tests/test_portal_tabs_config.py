"""08 — PUT /api/config/tabs Admin đổi tên/thứ tự."""


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


def test_hr_cannot_put_tabs(client):
    r = client.put("/api/config/tabs", headers=_hr_headers(client), json={"tabs": []})
    assert r.status_code == 403


def test_admin_rename_and_reorder(client):
    headers = _admin_headers(client)
    listed = client.get("/api/config/tabs", headers=headers)
    assert listed.status_code == 200
    tabs = listed.json()
    assert len(tabs) == 8

    # Đổi tên overview + đảo sort với hr
    by_key = {t["key"]: dict(t) for t in tabs}
    by_key["overview"]["name"] = "Tổng Quan Nhà Máy"
    so_ov = by_key["overview"]["sort_order"]
    so_hr = by_key["hr"]["sort_order"]
    by_key["overview"]["sort_order"] = so_hr
    by_key["hr"]["sort_order"] = so_ov

    payload = {
        "tabs": [
            {
                "key": t["key"],
                "name": t["name"],
                "description": t["description"],
                "sort_order": t["sort_order"],
                "enabled": t["enabled"],
            }
            for t in by_key.values()
        ]
    }
    saved = client.put("/api/config/tabs", headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    names = {t["key"]: t["name"] for t in saved.json()}
    assert names["overview"] == "Tổng Quan Nhà Máy"

    portal = client.get("/api/portal/tabs", headers=headers)
    assert portal.status_code == 200
    pnames = {t["key"]: t["name"] for t in portal.json()["tabs"]}
    assert pnames["overview"] == "Tổng Quan Nhà Máy"


def test_cannot_disable_config(client):
    headers = _admin_headers(client)
    tabs = client.get("/api/config/tabs", headers=headers).json()
    for t in tabs:
        if t["key"] == "config":
            t["enabled"] = False
    r = client.put(
        "/api/config/tabs",
        headers=headers,
        json={
            "tabs": [
                {
                    "key": t["key"],
                    "name": t["name"],
                    "description": t["description"],
                    "sort_order": t["sort_order"],
                    "enabled": t["enabled"],
                }
                for t in tabs
            ]
        },
    )
    assert r.status_code == 400
    assert "Cấu Hình" in r.json()["detail"] or "is_system" in r.json()["detail"]


def test_reset_tabs(client):
    headers = _admin_headers(client)
    tabs = client.get("/api/config/tabs", headers=headers).json()
    for t in tabs:
        if t["key"] == "overview":
            t["name"] = "XXX"
    client.put(
        "/api/config/tabs",
        headers=headers,
        json={
            "tabs": [
                {
                    "key": t["key"],
                    "name": t["name"],
                    "description": t["description"],
                    "sort_order": t["sort_order"],
                    "enabled": t["enabled"],
                }
                for t in tabs
            ]
        },
    )
    reset = client.post("/api/config/tabs/reset", headers=headers)
    assert reset.status_code == 200
    names = {t["key"]: t["name"] for t in reset.json()}
    assert names["overview"] == "Tổng Quan"
