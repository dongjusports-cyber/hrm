"""Hạng mục 2.5 — bảng chính sách có ngày hiệu lực + tra thâm niên 136 tháng = 550.000."""

from decimal import Decimal


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_insurance_rates_current(client):
    headers = _hr_headers(client)
    res = client.get("/api/policies/insurance-rates/current", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert Decimal(str(body["si_employee_pct"])) == Decimal("8")
    assert Decimal(str(body["hi_employee_pct"])) == Decimal("1.5")
    assert Decimal(str(body["ui_employee_pct"])) == Decimal("1")
    assert Decimal(str(body["union_pct"])) == Decimal("44100")
    assert Decimal(str(body["si_base_cap"])) == Decimal("46800000")


def test_pit_brackets_seven_tiers(client):
    headers = _hr_headers(client)
    res = client.get("/api/policies/pit-brackets", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert len(rows) == 7
    assert rows[0]["seq"] == 1
    assert Decimal(str(rows[0]["rate_percent"])) == Decimal("5")
    assert Decimal(str(rows[-1]["rate_percent"])) == Decimal("35")


def test_pit_deductions(client):
    headers = _hr_headers(client)
    res = client.get("/api/policies/pit-deductions/current", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert Decimal(str(body["self_amount"])) == Decimal("11000000")
    assert Decimal(str(body["dependent_amount"])) == Decimal("4400000")


def test_seniority_136_months_is_550000(client):
    """Nghiệm thu đợt 2 (24§): Bậc thâm niên 136 tháng tra ra 550.000."""
    headers = _hr_headers(client)
    res = client.get("/api/policies/seniority-amount?months=136", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert Decimal(str(body["amount"])) == Decimal("550000")
    assert body["months_from"] == 120
    assert body["months_to"] == 191


def test_seniority_formula_band_18_months(client):
    """18 tháng ∈ 6–119 → FLOOR(18/6)×25.000 = 75.000 (F_CAL_SERVERANCE)."""
    headers = _hr_headers(client)
    res = client.get("/api/policies/seniority-amount?months=18", headers=headers)
    assert res.status_code == 200, res.text
    assert Decimal(str(res.json()["amount"])) == Decimal("75000")


def test_seniority_under_6_months_is_zero(client):
    headers = _hr_headers(client)
    res = client.get("/api/policies/seniority-amount?months=5", headers=headers)
    assert res.status_code == 200, res.text
    assert Decimal(str(res.json()["amount"])) == Decimal("0")


def test_attendance_bonus_rules_match_genus_and_hien_phap(client):
    headers = _hr_headers(client)
    res = client.get("/api/policies/attendance-bonus-rules/current", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["late_count_half"] == 2
    assert body["early_count_half"] == 2
    assert body["late_count_zero"] == 5
    assert body["early_count_zero"] == 5
    assert set(body["exempt_leave_codes"]) == {"ALE", "FLE", "WED"}
    assert Decimal(str(body["full_amount"])) == Decimal("600000")
