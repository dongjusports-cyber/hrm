"""P3.3 — OT base ≠ SI base; neo MSNV 5290 Excel Oct/2025."""

from decimal import Decimal

from app.modules.payroll.engine_allowances import AllowanceLine
from app.modules.payroll.engine_ot import OtHours, OtInput, compute_ot_pay
from app.modules.policy.seed_payload import default_payload


def _lines_5290_excel() -> list[AllowanceLine]:
    """Fixture khớp ví dụ 03§3.5: SI 6.325.000 = HĐ + độc hại + thâm niên 550k."""
    return [
        AllowanceLine("ATTEND", "Chuyên cần", Decimal("230000"), Decimal("238846"), False, True),
        AllowanceLine("TRANSPORT", "Đi lại", Decimal("760000"), Decimal("789231"), False, False),
        AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True),
        AllowanceLine("SENIORITY", "Thâm niên", Decimal("550000"), Decimal("550000"), True, True),
    ]


def test_ot_5290_neo_excel():
    # base = 6.325.000 + 230.000 = 6.555.000; /26/8*1.5*27h = 1.276.334đ
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=_lines_5290_excel(),
            attend_full_monthly=Decimal("230000"),
            hours=OtHours(weekday=Decimal("27")),
            policy=default_payload(),
        )
    )
    assert r.si_contribution_base == Decimal("6325000")
    assert r.ot_base == Decimal("6555000")
    assert r.ot_pay == Decimal("1276334")


def test_ot_must_not_use_si_base_alone():
    """Dùng nhầm SI base làm OT base → lệch ~45k — bắt buộc fail nếu sai."""
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=_lines_5290_excel(),
            attend_full_monthly=Decimal("230000"),
            hours=OtHours(weekday=Decimal("27")),
            policy=default_payload(),
        )
    )
    wrong = Decimal("6325000") / Decimal("26") / Decimal("8") * Decimal("1.5") * Decimal("27")
    assert r.ot_pay != wrong.quantize(Decimal("1"))
    assert r.ot_base == r.si_contribution_base + Decimal("230000")


def test_ot_weekend_rate():
    lines = [
        AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True),
    ]
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=lines,
            attend_full_monthly=Decimal("0"),
            hours=OtHours(weekend=Decimal("8")),
            policy=default_payload(),
        )
    )
    # ot_base = 5675000+100000 = 5775000; hourly*2.0*8
    assert r.ot_base == Decimal("5775000")
    assert r.ot_pay > 0
