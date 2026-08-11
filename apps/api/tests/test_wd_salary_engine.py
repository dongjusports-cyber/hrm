"""P3.1 — unit wd_salary (Decimal, neo Oct/2025)."""

from datetime import date
from decimal import Decimal

from app.modules.payroll.engine_wd import WdSalaryInput, compute_wd_salary


def _inp(**kwargs) -> WdSalaryInput:
    base = dict(
        contract_salary=Decimal("5675000"),
        probation_salary=Decimal("4840750"),
        salary_divisor=Decimal("26"),
        worked_days=Decimal("27"),
        al_days=Decimal("0"),
        period_from=date(2025, 10, 1),
        period_to=date(2025, 10, 31),
        contract_signed_at=date(2020, 4, 15),
        work_weekdays=(1, 2, 3, 4, 5, 6),
        holiday_dates=frozenset(),
    )
    base.update(kwargs)
    return WdSalaryInput(**base)


def test_wd_official_5290_oct_2025():
    # 5.675.000/26*27 = 5.893.269đ (03§3.3)
    r = compute_wd_salary(_inp())
    assert r.wd_salary == Decimal("5893269")
    assert r.probation_days == 0
    assert r.contract_days == Decimal("27")


def test_wd_probation_pure():
    # 4.840.750/26*19 = 3.537.471đ
    r = compute_wd_salary(
        _inp(
            contract_salary=Decimal("5675000"),
            probation_salary=Decimal("4840750"),
            worked_days=Decimal("19"),
            contract_signed_at=None,
        )
    )
    assert r.wd_salary == Decimal("3537471")
    assert r.probation_days == Decimal("19")


def test_wd_with_al_days():
    # 4.2: AL không gộp WD — chỉ 26 ngày công
    r = compute_wd_salary(_inp(worked_days=Decimal("26"), al_days=Decimal("1")))
    assert r.wd_salary == Decimal("5675000")
    assert r.al_days == Decimal("1")


def test_wd_idempotent_decimal():
    a = compute_wd_salary(_inp())
    b = compute_wd_salary(_inp())
    assert a.wd_salary == b.wd_salary
