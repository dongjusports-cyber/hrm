"""2.4 — work_shifts + team_shift_schedules (Admin API)."""

from datetime import date, timedelta


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_work_shifts_and_team_default(client):
    headers = _admin_headers(client)
    shifts = client.get("/api/config/catalog/work-shifts", headers=headers)
    assert shifts.status_code == 200
    codes = {x["code"] for x in shifts.json()}
    assert "ADMIN" in codes

    teams = client.get("/api/config/org/teams", headers=headers)
    assert teams.status_code == 200
    team = teams.json()[0]
    team_id = team["id"]

    patch = client.patch(
        f"/api/config/org/teams/{team_id}/default-shift",
        headers=headers,
        json={"default_shift_id": "ADMIN"},
    )
    assert patch.status_code == 200
    assert patch.json()["default_shift_id"] == "ADMIN"

    work_date = date.today() + timedelta(days=7)
    eff = client.get(
        "/api/config/catalog/team-shift-schedules/effective",
        headers=headers,
        params={"team_id": team_id, "work_date": work_date.isoformat()},
    )
    assert eff.status_code == 200
    assert eff.json()["work_shift_id"] == "ADMIN"
    assert eff.json()["source"] in ("team_default", "override")


def test_team_shift_schedule_override(client):
    headers = _admin_headers(client)
    client.get("/api/config/catalog/work-shifts", headers=headers)
    team_id = client.get("/api/config/org/teams", headers=headers).json()[0]["id"]
    work_date = (date.today() + timedelta(days=14)).isoformat()

    created = client.post(
        "/api/config/catalog/team-shift-schedules",
        headers=headers,
        json={
            "team_id": team_id,
            "work_date": work_date,
            "work_shift_id": "ADMIN",
            "note": "test 2.4",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["work_shift_id"] == "ADMIN"
    assert body["note"] == "test 2.4"

    listed = client.get(
        "/api/config/catalog/team-shift-schedules",
        headers=headers,
        params={"team_id": team_id, "date_from": work_date, "date_to": work_date},
    )
    assert listed.status_code == 200
    assert any(r["id"] == body["id"] for r in listed.json())

    eff = client.get(
        "/api/config/catalog/team-shift-schedules/effective",
        headers=headers,
        params={"team_id": team_id, "work_date": work_date},
    )
    assert eff.status_code == 200
    assert eff.json()["source"] == "override"
