"""P3.4 — BHXH/BHYT/BHTN/CD + net."""

from decimal import Decimal

from app.modules.payroll.engine_insurance import InsuranceInput, compute_insurance_and_net
from app.modules.policy.seed_payload import default_payload


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
    assert r.net == Decimal("10000000") - Decimal("506000") - Decimal("94875") - Decimal("63250") - Decimal(
        "44100"
    )


def test_si_not_enrolled_zero_insurance():
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
    assert r.union_fee == Decimal("44100")
    assert r.net == Decimal("5000000") - Decimal("44100")


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
