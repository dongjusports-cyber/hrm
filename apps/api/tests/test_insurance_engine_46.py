"""4.6 — BHXH trần + taxable_income tách khỏi net (22§22.9–22.10)."""

from decimal import Decimal

from app.modules.payroll.component_bases import apply_si_base_cap
from app.modules.payroll.engine_insurance import InsuranceInput, compute_insurance_and_net
from app.modules.policy.seed_payload import default_payload


def test_si_base_cap_468m():
    capped, raw = apply_si_base_cap(Decimal("50000000"), default_payload())
    assert capped == Decimal("46800000")
    assert raw == Decimal("50000000")


def test_insurance_applies_cap():
    policy = default_payload()
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("50000000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=Decimal("55000000"),
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=policy,
        )
    )
    assert r.si_base_used == Decimal("46800000")
    assert r.si_base_raw == Decimal("50000000")
    assert r.bhxh == Decimal("3744000")
    assert r.bhyt == Decimal("702000")
    assert r.bhtn == Decimal("468000")


def test_taxable_income_equals_gross_minus_mandatory_si():
    gross = Decimal("10659423")
    r = compute_insurance_and_net(
        InsuranceInput(
            si_contribution_base=Decimal("8885000"),
            si_enrolled=True,
            si_base_override=None,
            union_fee_override=None,
            gross=gross,
            other_deductions=Decimal("0"),
            other_adjustments=Decimal("0"),
            policy=default_payload(),
        )
    )
    assert r.taxable_income == gross - r.bhxh - r.bhyt - r.bhtn
    assert r.net == gross - r.bhxh - r.bhyt - r.bhtn - r.union_fee - r.pit_amount


def test_5290_insurance_unchanged_below_cap():
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
    assert r.si_base_used == Decimal("6325000")
    assert r.taxable_income == Decimal("10000000") - Decimal("506000") - Decimal("94875") - Decimal("63250")
