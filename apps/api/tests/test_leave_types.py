"""Hạng mục 2.2 — leave_types mở rộng: đủ 14 mã thật với pay_ratio_percent (22§22.6)."""


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_leave_types_has_14_codes(client):
    headers = _hr_headers(client)
    res = client.get("/api/attendance/leave-types", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    codes = {r["code"] for r in rows}
    assert codes == {
        "ALE", "FLE", "WED", "LA", "OFF", "TMP", "PT", "MLE", "MC", "SLE", "SCH", "NOP", "NON", "PER",
    }
    assert len(rows) == 14


def test_leave_types_pay_ratio_percent_matches_226(client):
    headers = _hr_headers(client)
    rows = {r["code"]: r for r in client.get("/api/attendance/leave-types", headers=headers).json()}

    for code in ("ALE", "FLE", "WED", "LA", "OFF"):
        assert rows[code]["pay_ratio_percent"] == 100, code
    assert rows["TMP"]["pay_ratio_percent"] == 70
    for code in ("PT", "MLE", "MC", "SLE", "SCH", "NOP", "NON"):
        assert rows[code]["pay_ratio_percent"] == 0, code


def test_leave_types_per_ratio_is_null_not_guessed(client):
    """GenusSuite bỏ trống % trả lương của PER — buộc HR khai báo, không được đoán (N4)."""
    headers = _hr_headers(client)
    rows = {r["code"]: r for r in client.get("/api/attendance/leave-types", headers=headers).json()}
    assert rows["PER"]["pay_ratio_percent"] is None


def test_leave_types_paid_by_si_flags(client):
    headers = _hr_headers(client)
    rows = {r["code"]: r for r in client.get("/api/attendance/leave-types", headers=headers).json()}
    for code in ("PT", "MLE", "MC", "SLE", "SCH"):
        assert rows[code]["paid_by_si"] is True, code
    for code in ("ALE", "FLE", "WED", "LA", "OFF", "TMP", "NOP", "NON", "PER"):
        assert rows[code]["paid_by_si"] is False, code


def test_leave_types_affects_attendance_bonus_only_for_nop_non(client):
    """Chỉ NOP/NON "tính là vắng → mất sạch chuyên cần" theo 22§22.6."""
    headers = _hr_headers(client)
    rows = {r["code"]: r for r in client.get("/api/attendance/leave-types", headers=headers).json()}
    assert rows["NOP"]["affects_attendance_bonus"] is True
    assert rows["NON"]["affects_attendance_bonus"] is True
    for code in ("ALE", "FLE", "WED", "LA", "OFF", "TMP", "PT", "MLE", "MC", "SLE", "SCH", "PER"):
        assert rows[code]["affects_attendance_bonus"] is False, code


def test_leave_types_seed_is_idempotent(client):
    headers = _hr_headers(client)
    client.get("/api/attendance/leave-types", headers=headers)
    first = client.get("/api/attendance/leave-types", headers=headers).json()
    client.get("/api/attendance/leave-types", headers=headers)
    second = client.get("/api/attendance/leave-types", headers=headers).json()
    assert len(first) == len(second) == 14
