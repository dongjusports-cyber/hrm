"""OT ngoài — làm tròn 30p + công thức 22§22.8 (không qua payslip)."""

from decimal import Decimal

from app.modules.payroll.engine_allowances import AllowanceLine
from app.modules.payroll.engine_ot import OtHours, OtInput, compute_ot_pay, quantize_ot_hours
from app.modules.payroll.ot_external import _external_rate
from app.modules.policy.seed_payload import default_payload


def test_external_rate_from_policy():
    policy = default_payload()
    assert _external_rate(policy) == Decimal("1.5")
    policy["ot_split"]["ot_external"]["rate_key"] = "weekday"
    assert _external_rate(policy) == Decimal("1.5")


def test_external_hours_quantized_per_minute():
    policy = default_payload()
    assert quantize_ot_hours(Decimal("2.4"), policy) == Decimal("2.40")
    assert quantize_ot_hours(Decimal("0.25"), policy) == Decimal("0.25")


def test_external_pay_same_formula_as_weekday_ot():
    lines = [
        AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True),
    ]
    policy = default_payload()
    hours = Decimal("2.0")
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=lines,
            attend_full_monthly=Decimal("0"),
            hours=OtHours(weekday=hours),
            policy=policy,
        )
    )
    assert r.ot_pay > 0
    assert r.detail["effective_hours"]["weekday"] == "2.00"
