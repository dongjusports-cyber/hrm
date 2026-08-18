"""P3.4 — BHXH/BHYT/BHTN/CD + net."""

from datetime import date
from decimal import Decimal

from app.modules.payroll.engine_insurance import InsuranceInput, compute_insurance_and_net
from app.modules.policy.seed_payload import default_payload, normalize_si_policy


def test_insurance_5290_si_base():
    # SI 6.325.000 × 8% / 1.5% / 1% + CD 44.100
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("10000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
        )
    )
    assert r.bhxh == Decimal("506000")
    assert r.bhyt == Decimal("94875")
    assert r.bhtn == Decimal("63250")
    assert r.union_fee == Decimal("44100")
    assert r.pit_amount == Decimal("0")
    assert r.si_charged is True
    assert r.si_base_charged == Decimal("6325000")
    assert r.net == Decimal("10000000") - Decimal("506000") - Decimal("94875") - Decimal("63250") - Decimal(
        "44100"
    )


def test_si_not_enrolled_zero_insurance_and_union():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=False,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("5000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
        )
    )
    assert r.bhxh == r.bhyt == r.bhtn == Decimal("0")
    assert r.union_fee == Decimal("0")
    assert r.si_charged is False
    assert r.si_base_charged == Decimal("0")
    assert r.net == Decimal("5000000")


def test_si_base_override():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=Decimal("5000000"),
            union_fee_override=Decimal("0"),
            gross=Decimal("8000000"),
            other_deductions=Decimal("100000"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
        )
    )
    assert r.si_base_used == Decimal("5000000")
    assert r.bhxh == Decimal("400000")
    assert r.union_fee == Decimal("0")
    assert r.net == Decimal("8000000") - Decimal("400000") - Decimal("75000") - Decimal("50000") - Decimal(
        "100000"
    )


def test_si_under_12_still_employed_charges():
    """NV cũ còn làm qua ngày 16 — đóng cả tháng dù mới 11.87 công."""
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("2000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
            worked_days=Decimal("11.87"),
            period_start=date(2026, 8, 1),
            join_date=date(2017, 3, 8),
            resign_date=None,
        )
    )
    assert r.si_charged is True
    assert r.bhxh == Decimal("506000")
    assert r.union_fee == Decimal("44100")


def test_si_join_from_day_16_under_12_no_charge():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("2000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
            worked_days=Decimal("11.99"),
            period_start=date(2026, 8, 1),
            join_date=date(2026, 8, 16),
        )
    )
    assert r.bhxh == r.union_fee == Decimal("0")
    assert r.si_charged is False


def test_si_12_worked_days_from_day_16_charges():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("10000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
            worked_days=Decimal("12"),
            period_start=date(2026, 8, 1),
            resign_date=None,
        )
    )
    assert r.bhxh == Decimal("506000")
    assert r.union_fee == Decimal("44100")
    assert r.si_base_charged == Decimal("6325000")


def test_si_resign_day_15_even_with_12_days_no_charge():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("5000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
            worked_days=Decimal("12"),
            period_start=date(2026, 8, 1),
            resign_date=date(2026, 8, 15),
        )
    )
    assert r.bhxh == r.union_fee == Decimal("0")
    assert r.si_charged is False


def test_si_join_after_16_with_12_days_still_charges():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("10000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
            worked_days=Decimal("12"),
            period_start=date(2026, 8, 1),
            resign_date=None,
            join_date=date(2026, 8, 18),
        )
    )
    assert r.si_charged is True
    assert r.union_fee == Decimal("44100")


def test_si_maternity_leave_pauses_all_bh_and_union():
    """Nghỉ thai sản giao kỳ — BHXH/BHYT/BHTN + công đoàn = 0."""
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("10000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
            worked_days=Decimal("0"),
            period_start=date(2026, 8, 1),
            join_date=date(2017, 3, 8),
            on_maternity_leave=True,
        )
    )
    assert r.bhxh == r.bhyt == r.bhtn == Decimal("0")
    assert r.union_fee == Decimal("0")
    assert r.si_charged is False
    assert r.net == Decimal("10000000")


def test_normalize_old_policy_si_components():
    old = {"si_base_components": ["BASIC", "POS", "TECH", "SENIORITY", "TRAIN", "TREAT"]}
    out = normalize_si_policy(old)
    assert "PCCC" in out["si_base_components"]
    assert "HSE" in out["si_base_components"]
    assert "TRAIN" not in out["si_base_components"]
    assert out["si_month_rule"]["min_worked_days"] == 12
    assert out["si_month_rule"]["from_day_of_month"] == 16
    assert out["ot_split"]["on_books_after"] == "17:30"
    assert out["ot_split"]["ot_grace_minutes"] == 30


def test_normalize_old_ot_grace_1715():
    old = {"ot_split": {"on_books_after": "17:15", "ot_grace_minutes": 15}}
    out = normalize_si_policy(old)
    assert out["ot_split"]["on_books_after"] == "17:30"
    assert out["ot_split"]["ot_grace_minutes"] == 30
    assert out["ot_split"]["ignore_punches_from"] == "17:00"
    assert out["ot_split"]["ignore_punches_until"] == "17:30"
