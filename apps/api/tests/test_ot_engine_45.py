"""4.5 — OT theo 22§22.8: nền policy, làm tròn 30p, lễ >8h."""

from decimal import Decimal

from app.modules.payroll.money import money_vnd
from app.modules.payroll.engine_allowances import AllowanceLine
from app.modules.payroll.engine_ot import OtHours, OtInput, compute_ot_pay, quantize_ot_hours
from app.modules.payroll.component_bases import compute_si_and_ot_bases
from app.modules.policy.seed_payload import default_payload


def _lines_5290_excel() -> list[AllowanceLine]:
    return [
        AllowanceLine("ATTEND", "Chuyên cần", Decimal("230000"), Decimal("238846"), False, True),
        AllowanceLine("TRANSPORT", "Đi lại", Decimal("760000"), Decimal("789231"), False, False),
        AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True),
        AllowanceLine("SENIORITY", "Thâm niên", Decimal("550000"), Decimal("550000"), True, True),
    ]


def test_ot_bases_from_policy_components():
    policy = default_payload()
    si, ot, detail = compute_si_and_ot_bases(
        contract_salary=Decimal("5675000"),
        allowance_lines=_lines_5290_excel(),
        attend_full_monthly=Decimal("230000"),
        policy=policy,
    )
    assert si == Decimal("6325000")
    assert ot == Decimal("6555000")
    assert "INDUS" in detail["ot_base_components"]
    assert "INDUS" not in detail["si_base_components"]


def test_ot_5290_neo_still_holds():
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
    assert r.ot_pay == Decimal("1276334")
    assert r.ot_base == Decimal("6555000")
    assert r.si_contribution_base == Decimal("6325000")


def test_ot_hours_floor_30_minutes():
    policy = default_payload()
    assert quantize_ot_hours(Decimal("2.5"), policy) == Decimal("2.50")
    assert quantize_ot_hours(Decimal("2.4"), policy) == Decimal("2.00")
    assert quantize_ot_hours(Decimal("0.25"), policy) == Decimal("0")


def test_ot_weekday_below_30_minutes_zero_pay():
    lines = [AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True)]
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=lines,
            attend_full_monthly=Decimal("0"),
            hours=OtHours(weekday=Decimal("0.25")),
            policy=default_payload(),
        )
    )
    assert r.ot_pay == 0


def test_ot_holiday_over_8_tiered():
    lines = [AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True)]
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=lines,
            attend_full_monthly=Decimal("0"),
            hours=OtHours(holiday=Decimal("10")),
            policy=default_payload(),
        )
    )
    hourly = Decimal("5775000") / Decimal("26") / Decimal("8")
    expected = money_vnd(hourly * Decimal("8") * Decimal("2") + hourly * Decimal("2") * Decimal("3"))
    assert r.ot_pay == expected
    types = [p["type"] for p in r.detail["parts"]]
    assert "holiday" in types
    assert "holiday_over_8" in types


def test_si_base_excludes_transport_and_attend():
    si, ot, _ = compute_si_and_ot_bases(
        contract_salary=Decimal("5675000"),
        allowance_lines=_lines_5290_excel(),
        attend_full_monthly=Decimal("230000"),
        policy=default_payload(),
    )
    assert si + Decimal("230000") + Decimal("760000") != ot
    assert ot - si == Decimal("230000")
