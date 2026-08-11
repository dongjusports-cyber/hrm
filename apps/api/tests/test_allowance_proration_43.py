"""4.3 — tử số chia phụ cấp (22§22.3)."""

from datetime import date
from decimal import Decimal

from app.modules.payroll.allowance_proration import compute_numerator_days, prorate_allowance
from app.modules.payroll.engine_allowances import AllowanceInput, AllowanceTypeView, compute_allowances
from app.modules.policy.seed_payload import default_payload


def test_numerator_wt_only():
    total, parts = compute_numerator_days(
        worked_days=Decimal("27"),
        leave_days_by_code={},
        policy=default_payload(),
    )
    assert total == Decimal("27")
    assert parts["WT"] == "27"


def test_numerator_includes_ale_excludes_tmp():
    total, parts = compute_numerator_days(
        worked_days=Decimal("26"),
        leave_days_by_code={"ALE": Decimal("1"), "TMP": Decimal("2")},
        policy=default_payload(),
    )
    assert total == Decimal("27")
    assert parts["ALE"] == "1"
    assert "TMP" not in parts


def test_numerator_com_maps_off():
    total, _ = compute_numerator_days(
        worked_days=Decimal("25"),
        leave_days_by_code={"OFF": Decimal("2")},
        policy=default_payload(),
    )
    assert total == Decimal("27")


def test_prorate_attend_27_days_cap_divisor_26():
    # 600.000 / 26 × 27 = 623.077 (22§22.3 kiểm chứng)
    amt = prorate_allowance(Decimal("600000"), Decimal("26"), Decimal("27"))
    assert amt.quantize(Decimal("1")) == Decimal("623077")


def test_prorate_tet_month_20_days():
    amt = prorate_allowance(Decimal("600000"), Decimal("20"), Decimal("20"))
    assert amt == Decimal("600000")


def test_compute_ale_adds_to_attend_when_worked_26():
    types = [
        AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000")),
        AllowanceTypeView("TRANSPORT", "Đi lại", "by_worked_days", False, False, Decimal("800000")),
    ]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=date(2020, 1, 15),
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=types,
            leave_days_by_code={"ALE": Decimal("1")},
        )
    )
    assert r.numerator_days == Decimal("27")
    by = {x.code: x.amount for x in r.lines}
    assert by["ATTEND"] == Decimal("623077")
    assert by["TRANSPORT"] == Decimal("830769")


def test_tmp_does_not_increase_numerator():
    types = [
        AllowanceTypeView("ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000")),
    ]
    r = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=None,
            as_of=date(2025, 10, 31),
            policy=default_payload(),
            monthly_by_code={},
            types=types,
            leave_days_by_code={"TMP": Decimal("3")},
        )
    )
    assert r.numerator_days == Decimal("26")
    assert r.lines[0].amount == Decimal("600000")
