"""P6.2 — TNCN progressive + cờ pit_enabled."""

from decimal import Decimal

from app.modules.payroll.engine_insurance import InsuranceInput, compute_insurance_and_net
from app.modules.payroll.engine_pit import compute_pit_amount, compute_progressive_pit
from app.modules.policy.seed_payload import default_payload


def test_progressive_first_bracket():
    # 3.000.000 × 5% = 150.000
    assert compute_progressive_pit(
        Decimal("3000000"),
        default_payload()["pit_brackets"],
    ) == Decimal("150000")


def test_progressive_cross_brackets():
    # 6.000.000 → 5M×5% + 1M×10% = 250.000 + 100.000 = 350.000
    assert compute_progressive_pit(
        Decimal("6000000"),
        default_payload()["pit_brackets"],
    ) == Decimal("350000")


def test_pit_disabled_by_default_in_insurance():
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("20000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
        )
    )
    assert r.pit_amount == Decimal("0")


def test_pit_enabled_computes_tax():
    policy = default_payload()
    policy["pit_enabled"] = True
    # gross 20M, BH on 6.325M → bhxh 506k + bhyt 94875 + bhtn 63250 = 664125
    # assessable = 20000000 - 664125 = 19335875
    # taxable = 19335875 - 11000000 - 0 = 8335875
    # tax: 5M×5% + 3.335875M×10% = 250000 + 333587.5 → 583588 (HALF_UP)
    pit, detail = compute_pit_amount(
        gross=Decimal("20000000"),
        bhxh=Decimal("506000"),
        bhyt=Decimal("94875"),
        bhtn=Decimal("63250"),
        tax_dependent_count=0,
        pit_enrolled=True,
        policy=policy,
    )
    assert pit == Decimal("583588")
    assert detail["taxable"] == "8335875"

    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("6325000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=Decimal("0"),
            gross=Decimal("20000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=policy,
            tax_dependent_count=0,
            pit_enrolled=True,
        )
    )
    assert r.pit_amount == Decimal("583588")
    assert r.net == Decimal("20000000") - Decimal("506000") - Decimal("94875") - Decimal("63250") - r.pit_amount


def test_pit_not_enrolled_zero():
    policy = default_payload()
    policy["pit_enabled"] = True
    pit, _ = compute_pit_amount(
        gross=Decimal("20000000"),
        bhxh=Decimal("0"),
        bhyt=Decimal("0"),
        bhtn=Decimal("0"),
        tax_dependent_count=0,
        pit_enrolled=False,
        policy=policy,
    )
    assert pit == Decimal("0")
