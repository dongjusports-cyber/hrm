"""2.6 — policy payload 22§22.12 + validator phạt chuyên cần 22§22.3."""

import pytest
from fastapi import HTTPException

from app.modules.policy.seed_payload import DEFAULT_POLICY_PAYLOAD, default_payload
from app.modules.policy.validator import validate_payload


def test_default_payload_has_22_12_blocks():
    p = default_payload()
    assert p["attendance_bonus_monthly"] == 600_000
    assert p["transport_monthly_default"] == 800_000
    assert p["divisor_rule"]["source"] == "calendar_working_days"
    assert p["divisor_rule"]["cap"] == 26
    pen = p["attendance_penalties"]
    assert pen["late_half"] == 2 and pen["early_half"] == 2
    assert pen["late_zero"] == 5 and pen["early_zero"] == 5
    assert pen["exempt_leave_codes"] == ["ALE", "FLE", "WED"]
    assert pen["exempt_requires_hours_lt"] == 8
    assert pen["exempt_requires_punch"] is True
    assert "probation" in p and "annual_leave" in p and "rounding" in p


def test_validate_rejects_legacy_exempt_leave_codes():
    bad = default_payload()
    bad["attendance_penalties"] = {
        **bad["attendance_penalties"],
        "exempt_leave_codes": ["AL", "MARRIAGE"],
    }
    with pytest.raises(HTTPException) as exc:
        validate_payload(bad)
    assert "ALE" in exc.value.detail


def test_validate_merges_missing_keys_from_default():
    partial = {"attendance_bonus_monthly": 600_000}
    merged = validate_payload(partial)
    assert merged["transport_monthly_default"] == DEFAULT_POLICY_PAYLOAD["transport_monthly_default"]
    assert merged["attendance_penalties"]["late_zero"] == 5
