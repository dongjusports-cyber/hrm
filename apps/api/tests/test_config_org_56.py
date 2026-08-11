"""5.6 — config org + catalog work-shifts."""


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_org_summary_and_positions(client):
    headers = _admin_headers(client)
    summary = client.get("/api/config/org/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["departments"] >= 1
    assert body["teams"] >= 1

    positions = client.get("/api/config/org/positions", headers=headers)
    assert positions.status_code == 200
    assert isinstance(positions.json(), list)

    jobs = client.get("/api/config/org/jobs", headers=headers)
    assert jobs.status_code == 200

    teams = client.get("/api/config/org/teams", headers=headers)
    assert teams.status_code == 200
    assert teams.json()[0]["department_code"]


def test_catalog_work_shifts(client):
    headers = _admin_headers(client)
    res = client.get("/api/config/catalog/work-shifts", headers=headers)
    assert res.status_code == 200
    codes = {x["code"] for x in res.json()}
    assert "ADMIN" in codes or len(codes) >= 1
