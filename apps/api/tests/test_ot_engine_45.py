"""4.5 — OT theo 22§22.8: nền policy, làm tròn 30p, lễ >8h."""

from decimal import Decimal

from app.modules.payroll.money import money_vnd
from app.modules.payroll.engine_allowances import AllowanceLine
from app.modules.payroll.engine_ot import OtHours, OtInput, buckets_from_parts, compute_ot_pay, quantize_ot_hours
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


def test_ot_hours_per_minute():
    policy = default_payload()
    assert quantize_ot_hours(Decimal("2.5"), policy) == Decimal("2.50")
    assert quantize_ot_hours(Decimal("2.4"), policy) == Decimal("2.40")
    assert quantize_ot_hours(Decimal("0.25"), policy) == Decimal("0.25")


def test_ot_weekday_15_minutes_has_pay():
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
    assert r.ot_pay > 0


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
    b = buckets_from_parts(r.detail["parts"])
    assert b.hours_x20 == Decimal("8")
    assert b.hours_x30 == Decimal("2")
    assert b.hours_x15 == 0
    assert abs(b.pay_x20 + b.pay_x30 - r.ot_pay) <= 1


def test_buckets_weekday_and_weekend():
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=[AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True)],
            attend_full_monthly=Decimal("0"),
            hours=OtHours(weekday=Decimal("2"), weekend=Decimal("4")),
            policy=default_payload(),
        )
    )
    b = buckets_from_parts(r.detail["parts"])
    assert b.hours_x15 == Decimal("2.00")
    assert b.hours_x20 == Decimal("4.00")
    assert b.hours_x21 == 0
    assert b.hours_x30 == 0
    assert b.pay_x15 > 0
    assert b.pay_x20 > b.pay_x15
    assert abs(b.pay_x15 + b.pay_x20 - r.ot_pay) <= 1


def test_ot_pay_by_time_band_rates():
    """Payslip/ATM: từng hệ số khung giờ, không gộp 4 mốc cũ."""
    lines = [AllowanceLine("TOXIC", "Độc hại", Decimal("100000"), Decimal("100000"), True, True)]
    r = compute_ot_pay(
        OtInput(
            contract_salary=Decimal("5675000"),
            salary_divisor=Decimal("26"),
            allowance_lines=lines,
            attend_full_monthly=Decimal("0"),
            hours=OtHours(by_rate={"1.5": Decimal("2"), "2.1": Decimal("1"), "4.5": Decimal("1")}),
            policy=default_payload(),
        )
    )
    hourly = Decimal("5775000") / Decimal("26") / Decimal("8")
    expected = money_vnd(hourly * Decimal("2") * Decimal("1.5") + hourly * Decimal("2.1") + hourly * Decimal("4.5"))
    assert r.ot_pay == expected
    assert r.detail.get("time_bands") is True
    types = [p["type"] for p in r.detail["parts"]]
    assert "x1.5" in types
    assert "x2.1" in types
    assert "x4.5" in types


def test_si_base_includes_pccc_hse_excludes_train_and_attend():
    lines = _lines_5290_excel() + [
        AllowanceLine("PCCC", "PCCC", Decimal("882000"), Decimal("882000"), True, True),
        AllowanceLine("HSE", "HSE", Decimal("50000"), Decimal("50000"), True, True),
        AllowanceLine("TRAINING", "Đào tạo", Decimal("100000"), Decimal("100000"), False, False),
    ]
    si, _ot, detail = compute_si_and_ot_bases(
        contract_salary=Decimal("5675000"),
        allowance_lines=lines,
        attend_full_monthly=Decimal("230000"),
        policy=default_payload(),
    )
    # 5.675.000 + độc hại 100k + thâm niên 550k + PCCC 882k + HSE 50k
    assert si == Decimal("7257000")
    assert "PCCC" in detail["si_base_components"]
    assert "HSE" in detail["si_base_components"]
    assert "TRAIN" not in detail["si_base_components"]
    assert "INDUS" not in detail["si_base_components"]


def test_si_base_excludes_transport_and_attend():
    si, ot, _ = compute_si_and_ot_bases(
        contract_salary=Decimal("5675000"),
        allowance_lines=_lines_5290_excel(),
        attend_full_monthly=Decimal("230000"),
        policy=default_payload(),
    )
    assert si + Decimal("230000") + Decimal("760000") != ot
    assert ot - si == Decimal("230000")
