"""P3.2 — unit phụ cấp + phạt chuyên cần."""

from datetime import date
from decimal import Decimal

from app.modules.payroll.engine_allowances import (
    AllowanceInput,
    AllowanceTypeView,
    attendance_keep_percent,
    compute_allowances,
    seniority_monthly,
)
from app.modules.policy.seed_payload import default_payload


def test_attend_keep_late_3_to_4():
    pen = default_payload()["attendance_penalties"]
    assert attendance_keep_percent(late_count=3, early_count=0, absent_days=0, penalties=pen) == 50
    assert attendance_keep_percent(late_count=5, early_count=0, absent_days=0, penalties=pen) == 0


def test_attend_keep_early_or_absent():
    pen = default_payload()["attendance_penalties"]
    assert attendance_keep_percent(late_count=0, early_count=2, absent_days=0, penalties=pen) == 50
    assert attendance_keep_percent(late_count=0, early_count=0, absent_days=Decimal("2"), penalties=pen) == 0


def test_attend_keep_takes_worst():
    pen = default_payload()["attendance_penalties"]
    # trễ 3 (50%) + nghỉ 2 (0%) → 0
    assert attendance_keep_percent(late_count=3, early_count=0, absent_days=Decimal("2"), penalties=pen) == 0


def test_seniority_progressive():
    rules = {
        "tiers": [
            {"min_months": 6, "max_months": 120, "base": 25000, "per_6_months": 25000},
            {"min_months": 120, "max_months": 180, "fixed": 550000},
        ]
    }
    # 2020-01 → 2025-10 ≈ 69 tháng → 25000 + 10*25000 = 275000
    amt = seniority_monthly(date(2020, 1, 15), date(2025, 10, 31), rules)
    assert amt == Decimal("275000")


def test_attend_keep_any_absence_zero():
    pen = default_payload()["attendance_penalties"]
    assert attendance_keep_percent(late_count=0, early_count=0, absent_days=Decimal("1"), penalties=pen) == 0


def test_compute_attend_transport_toxic():
    types = [
        AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000")),
        AllowanceTypeView("TRANSPORT", "Đi lại", "by_worked_days", False, False, Decimal("800000")),
        AllowanceTypeView("TOXIC", "Độc hại", "by_worked_days", True, True, Decimal("100000")),
    ]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("27"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=date(2020, 1, 15),
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={"TOXIC": Decimal("100000")},
            types=types,
        )
    )
    by = {x.code: x.amount for x in r.lines}
    assert by["ATTEND"] == Decimal("623077")
    assert by["TRANSPORT"] == Decimal("830769")
    assert by["TOXIC"] == Decimal("103846")
    assert r.attend_keep_percent == 100
    assert r.allowance_total == by["ATTEND"] + by["TRANSPORT"] + by["TOXIC"]


def test_attend_penalty_halves():
    types = [
        AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000")),
    ]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("27"),
            late_count=3,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=None,
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=types,
        )
    )
    assert r.attend_keep_percent == 50
    assert r.lines[0].amount == Decimal("311538")
