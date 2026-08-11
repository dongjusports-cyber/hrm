"""P1.2 — Policy package + xác nhận 3 lần (P10)."""

from copy import deepcopy


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


def test_hr_cannot_access_policy(client):
    res = client.get("/api/policies/packages", headers=_hr_headers(client))
    assert res.status_code == 403


def test_list_seed_package(client):
    res = client.get("/api/policies/packages", headers=_admin_headers(client))
    assert res.status_code == 200
    assert len(res.json()) >= 1
    pkg = res.json()[0]
    assert pkg["name"] == "Mặc định 2025"
    assert pkg["payload"]["attendance_bonus_monthly"] == 600_000
    assert pkg["payload"]["ot_night_enabled"] is False


def test_put_requires_confirm_header(client):
    headers = _admin_headers(client)
    pkg = client.get("/api/policies/packages", headers=headers).json()[0]
    res = client.put(
        f"/api/policies/packages/{pkg['id']}",
        headers=headers,
        json={"payload": pkg["payload"]},
    )
    assert res.status_code == 400
    assert "3 bước" in res.json()["detail"]


def test_three_step_save_money_change(client):
    headers = _admin_headers(client)
    pkg = client.get("/api/policies/packages", headers=headers).json()[0]
    payload = deepcopy(pkg["payload"])
    payload["attendance_bonus_monthly"] = 630000

    step1 = client.put(
        f"/api/policies/packages/{pkg['id']}",
        headers={**headers, "X-Confirm-Step": "1"},
        json={"name": pkg["name"], "payload": payload},
    )
    assert step1.status_code == 200
    assert step1.json()["status"] == "need_confirm"
    assert step1.json()["step"] == 1
    assert "attendance_bonus_monthly" in step1.json()["changed_money_fields"]

    # Chưa lưu
    still = client.get(f"/api/policies/packages/{pkg['id']}", headers=headers).json()
    assert still["payload"]["attendance_bonus_monthly"] == 600_000

    step2 = client.put(
        f"/api/policies/packages/{pkg['id']}",
        headers={**headers, "X-Confirm-Step": "2"},
        json={"name": pkg["name"], "payload": payload},
    )
    assert step2.status_code == 200
    assert step2.json()["step"] == 2

    step3 = client.put(
        f"/api/policies/packages/{pkg['id']}",
        headers={**headers, "X-Confirm-Step": "3"},
        json={"name": pkg["name"], "payload": payload},
    )
    assert step3.status_code == 200, step3.text
    body = step3.json()
    assert body["status"] == "saved"
    assert body["package"]["payload"]["attendance_bonus_monthly"] == 630000
    assert body["package"]["version"] == pkg["version"] + 1


def test_reject_sql_and_invalid_si(client):
    headers = _admin_headers(client)
    pkg = client.get("/api/policies/packages", headers=headers).json()[0]
    bad = deepcopy(pkg["payload"])
    bad["sql"] = "drop table users"
    res = client.put(
        f"/api/policies/packages/{pkg['id']}",
        headers={**headers, "X-Confirm-Step": "1"},
        json={"payload": bad},
    )
    assert res.status_code == 400
    assert "SQL" in res.json()["detail"]

    bad2 = deepcopy(pkg["payload"])
    bad2["si_rates"]["bhxh"] = 8  # phải 0.08
    res2 = client.put(
        f"/api/policies/packages/{pkg['id']}",
        headers={**headers, "X-Confirm-Step": "1"},
        json={"payload": bad2},
    )
    assert res2.status_code == 400
