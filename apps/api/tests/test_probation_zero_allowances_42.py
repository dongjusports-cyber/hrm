"""4.2 — NV thử việc thuần: chuyên cần + đi lại = 0 (22§22.3 / policy.probation.zero_allowances)."""

from datetime import date
from decimal import Decimal

from app.modules.payroll.engine_allowances import (
    AllowanceInput,
    AllowanceTypeView,
    compute_allowances,
    should_zero_probation_allowances,
)
from app.modules.policy.seed_payload import default_payload


def _types() -> list[AllowanceTypeView]:
    return [
        AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000")),
        AllowanceTypeView("TRANSPORT", "Đi lại", "by_worked_days", False, False, Decimal("800000")),
    ]


def test_should_zero_when_unsigned_and_flag_on():
    assert (
        should_zero_probation_allowances(
            default_payload(),
            contract_signed_at=None,
            period_to=date(2026, 7, 31),
        )
        is True
    )


def test_should_zero_when_signed_after_period():
    assert (
        should_zero_probation_allowances(
            default_payload(),
            contract_signed_at=date(2026, 8, 15),
            period_to=date(2026, 7, 31),
        )
        is True
    )


def test_should_not_zero_when_already_official():
    assert (
        should_zero_probation_allowances(
            default_payload(),
            contract_signed_at=date(2020, 1, 1),
            period_to=date(2026, 7, 31),
        )
        is False
    )


def test_probation_pure_attend_and_transport_zero():
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=date(2026, 7, 1),
            as_of=date(2026, 7, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=_types(),
            suppress_allowances=True,
        )
    )
    by = {ln.code: ln.amount for ln in r.lines}
    assert by.get("ATTEND", Decimal("0")) == Decimal("0")
    assert by.get("TRANSPORT", Decimal("0")) == Decimal("0")
    assert r.allowance_total == Decimal("0")
    assert r.attend_full_monthly == Decimal("0")
    assert r.detail.get("suppress_allowances") is True


def test_official_still_gets_allowances():
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=date(2020, 1, 1),
            as_of=date(2026, 7, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=_types(),
            suppress_allowances=False,
        )
    )
    by = {ln.code: ln.amount for ln in r.lines}
    assert by["ATTEND"] == Decimal("600000")
    assert by["TRANSPORT"] == Decimal("800000")
