"""4.2 — lương ngày nghỉ tách khỏi WD."""

from datetime import date
from decimal import Decimal

from app.modules.payroll.engine_leave_pay import LeavePayInput, LeaveTypePayMeta, compute_leave_pay
from app.modules.payroll.engine_wd import WdSalaryInput, compute_wd_salary
from app.modules.payroll.money import money_vnd


def _wd_ctx(**kwargs) -> WdSalaryInput:
    base = dict(
        contract_salary=Decimal("5675000"),
        probation_salary=Decimal("4840750"),
        salary_divisor=Decimal("26"),
        worked_days=Decimal("26"),
        al_days=Decimal("0"),
        period_from=date(2025, 10, 1),
        period_to=date(2025, 10, 31),
        contract_signed_at=date(2020, 4, 15),
        work_weekdays=(1, 2, 3, 4, 5, 6),
        holiday_dates=frozenset(),
        sal_allow=Decimal("0"),
    )
    base.update(kwargs)
    return WdSalaryInput(**base)


def _leave_types() -> dict[str, LeaveTypePayMeta]:
    return {
        "ALE": LeaveTypePayMeta("ALE", "Nghỉ phép năm", 100),
        "TMP": LeaveTypePayMeta("TMP", "Nghỉ hết hàng", 70),
        "PER": LeaveTypePayMeta("PER", "Nghỉ có phép", None),
    }


def test_ale_100_one_day():
    wd = _wd_ctx()
    res = compute_leave_pay(
        LeavePayInput(
            contract_salary=wd.contract_salary,
            probation_salary=wd.probation_salary,
            sal_allow=wd.sal_allow,
            salary_divisor=wd.salary_divisor,
            wd_context=wd,
            leave_days_by_code={"ALE": Decimal("1")},
            leave_types=_leave_types(),
        )
    )
    assert res.leave_pay_total == Decimal("218269")
    assert len(res.lines) == 1
    assert res.lines[0].leave_code == "ALE"
    assert res.lines[0].segment == "official"


def test_tmp_70_one_day():
    wd = _wd_ctx()
    res = compute_leave_pay(
        LeavePayInput(
            contract_salary=wd.contract_salary,
            probation_salary=wd.probation_salary,
            sal_allow=wd.sal_allow,
            salary_divisor=wd.salary_divisor,
            wd_context=wd,
            leave_days_by_code={"TMP": Decimal("1")},
            leave_types=_leave_types(),
        )
    )
    assert res.leave_pay_total == Decimal("152788")


def test_wd_plus_ale_equals_legacy_combined():
    wd_inp = _wd_ctx(worked_days=Decimal("26"), al_days=Decimal("1"))
    wd_res = compute_wd_salary(wd_inp)
    leave_res = compute_leave_pay(
        LeavePayInput(
            contract_salary=wd_inp.contract_salary,
            probation_salary=wd_inp.probation_salary,
            sal_allow=wd_inp.sal_allow,
            salary_divisor=wd_inp.salary_divisor,
            wd_context=wd_inp,
            leave_days_by_code={"ALE": Decimal("1")},
            leave_types=_leave_types(),
        )
    )
    assert wd_res.wd_salary == Decimal("5675000")
    total = money_vnd(wd_res.wd_salary + leave_res.leave_pay_total)
    assert total == Decimal("5893269")


def test_per_skipped_when_ratio_not_set():
    wd = _wd_ctx()
    res = compute_leave_pay(
        LeavePayInput(
            contract_salary=wd.contract_salary,
            probation_salary=wd.probation_salary,
            sal_allow=wd.sal_allow,
            salary_divisor=wd.salary_divisor,
            wd_context=wd,
            leave_days_by_code={"PER": Decimal("2")},
            leave_types=_leave_types(),
        )
    )
    assert res.leave_pay_total == 0
    assert res.lines == []
    assert any(s["code"] == "PER" for s in res.detail["skipped"])


def test_probation_segment_mid_month_contract():
    wd = _wd_ctx(
        worked_days=Decimal("10"),
        contract_signed_at=date(2025, 10, 15),
    )
    leave_res = compute_leave_pay(
        LeavePayInput(
            contract_salary=wd.contract_salary,
            probation_salary=wd.probation_salary,
            sal_allow=wd.sal_allow,
            salary_divisor=wd.salary_divisor,
            wd_context=wd,
            leave_days_by_code={"ALE": Decimal("2")},
            leave_types=_leave_types(),
        )
    )
    segments = {ln.segment for ln in leave_res.lines}
    assert "official" in segments or "probation" in segments
    assert leave_res.leave_pay_total > 0
