"""Bước D — API chế độ về sớm (Thai sản / Nuôi con) 22§22.14."""

from datetime import date, timedelta


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_employee(client, headers, code: str) -> str:
    created = client.post(
        "/api/employees",
        headers=headers,
        json={
            "employee_code": code,
            "full_name": f"NV WT {code}",
            "team_code": "T1",
            "department_code": "SW1",
            "contract_salary": "6000000",
            "probation_salary": "5100000",
            "pay_channel": "ATM",
            "join_date": "2020-01-15",
            "contract_signed_at": "2020-01-15",
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_create_list_and_flag(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9301")
    today = date.today()
    body = {
        "regime_type": "CHILD",
        "hours_early": 2,
        "date_from": today.isoformat(),
        "date_to": (today + timedelta(days=30)).isoformat(),
        "note": "Nuôi con nhỏ",
    }
    res = client.post(f"/api/employees/{emp_id}/wt-regimes", headers=headers, json=body)
    assert res.status_code == 201, res.text
    r = res.json()
    assert r["regime_type"] == "CHILD"
    assert r["hours_early"] == 2
    assert r["ended_at"] is None

    listed = client.get(f"/api/employees/{emp_id}/wt-regimes", headers=headers).json()
    assert len(listed) == 1

    # Cờ wt_regime_active bật trên hồ sơ + tab «Chế độ đặc biệt»
    detail = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    assert detail["wt_regime_active"] is True
    special = client.get("/api/employees?status=special_regime", headers=headers).json()
    assert "9301" in {e["employee_code"] for e in special}


def test_validation_errors(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9302")
    today = date.today()

    # date_from quá khứ → 400 tiếng Việt
    past = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": (today - timedelta(days=1)).isoformat(),
            "date_to": (today + timedelta(days=10)).isoformat(),
        },
    )
    assert past.status_code == 400
    assert "hôm nay" in past.json()["detail"]

    # date_to < date_from → 400
    bad_range = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": (today + timedelta(days=10)).isoformat(),
            "date_to": (today + timedelta(days=5)).isoformat(),
        },
    )
    assert bad_range.status_code == 400


def test_overlap_rejected_then_end_frees(client):
    headers = _hr_headers(client)
    emp_id = _make_employee(client, headers, "9303")
    today = date.today()
    first = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "PREGNANT",
            "hours_early": 1,
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=60)).isoformat(),
        },
    )
    assert first.status_code == 201, first.text
    rid = first.json()["id"]

    # Chồng kỳ → 400
    dup = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": (today + timedelta(days=10)).isoformat(),
            "date_to": (today + timedelta(days=20)).isoformat(),
        },
    )
    assert dup.status_code == 400
    assert "chấm dứt" in dup.json()["detail"]

    # PATCH: đổi hours_early + date_to
    patched = client.patch(
        f"/api/employees/{emp_id}/wt-regimes/{rid}",
        headers=headers,
        json={"hours_early": 3, "date_to": (today + timedelta(days=90)).isoformat()},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["hours_early"] == 3

    # End → ended_at set, date_to = hôm nay
    ended = client.post(f"/api/employees/{emp_id}/wt-regimes/{rid}/end", headers=headers)
    assert ended.status_code == 200, ended.text
    assert ended.json()["ended_at"] is not None
    assert ended.json()["date_to"] == today.isoformat()

    # Sau khi chấm dứt → không còn hiệu lực, tab special_regime không chứa NV
    detail = client.get(f"/api/employees/{emp_id}", headers=headers).json()
    # date_to = hôm nay nên vẫn còn hiệu lực HÔM NAY; ngày mai mới hết.
    assert detail["wt_regime_active"] is True

    # Thêm mới sau khi đã chấm dứt (ended_at set) → không bị coi là chồng kỳ
    again = client.post(
        f"/api/employees/{emp_id}/wt-regimes",
        headers=headers,
        json={
            "regime_type": "CHILD",
            "hours_early": 2,
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=15)).isoformat(),
        },
    )
    assert again.status_code == 201, again.text
