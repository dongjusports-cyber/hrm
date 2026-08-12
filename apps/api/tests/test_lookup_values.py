"""Hạng mục 2.1 — lookup_values: danh mục phẳng dân tộc, tôn giáo, quốc tịch, nơi sinh,
nơi cấp CCCD, trình độ (21§21.4)."""


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_lookup_groups_lists_all_seven(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-groups", headers=headers)
    assert res.status_code == 200, res.text
    groups = set(res.json())
    assert groups == {
        "ethnicity",
        "religion",
        "nationality",
        "education_level",
        "birth_place",
        "id_issue_place",
        "marital_status",
    }


def test_lookup_values_ethnicity_has_54(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-values?group_code=ethnicity", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) == 54
    names = {r["name"] for r in rows}
    assert "Kinh" in names
    assert "Tày" in names
    # Thứ tự theo sort_order, Kinh đứng đầu (đông dân nhất, quy ước danh sách chính thức)
    assert rows[0]["name"] == "Kinh"


def test_lookup_values_birth_place_has_34_units_after_merger(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-values?group_code=birth_place", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) == 34
    assert rows[0]["name"] == "Hà Nội"
    assert rows[5]["name"] == "Thành phố Hồ Chí Minh"
    assert rows[6]["name"] == "Lai Châu"
    names = {r["name"] for r in rows}
    assert "Huế" in names
    assert "An Giang" in names


def test_lookup_values_id_issue_place_has_34_plus_cs(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-values?group_code=id_issue_place", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) == 35
    assert rows[-1]["name"] == "Cục Cảnh sát QLHC về TTXH"


def test_lookup_values_no_group_filter_returns_all_groups(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-values", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    groups_seen = {r["group_code"] for r in rows}
    assert groups_seen == {
        "ethnicity",
        "religion",
        "nationality",
        "education_level",
        "birth_place",
        "id_issue_place",
        "marital_status",
    }


def test_lookup_values_unknown_group_returns_empty(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-values?group_code=khong_ton_tai", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json() == []


def test_lookup_values_marital_status_codes(client):
    headers = _hr_headers(client)
    res = client.get("/api/lookup-values?group_code=marital_status", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    codes = {r["code"] for r in rows}
    assert codes >= {"single", "married", "divorced", "widowed"}


def test_lookup_values_seed_is_idempotent(client, db):
    """Gọi list nhiều lần không tạo dòng trùng (unique group_code+code)."""
    headers = _hr_headers(client)
    client.get("/api/lookup-values", headers=headers)
    res = client.get("/api/lookup-values?group_code=religion", headers=headers)
    client.get("/api/lookup-values", headers=headers)
    res2 = client.get("/api/lookup-values?group_code=religion", headers=headers)
    assert len(res.json()) == len(res2.json())
    assert len(res.json()) == 10
