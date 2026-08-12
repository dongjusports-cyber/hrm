"""Unit — employee_on_payroll_period."""

from datetime import date

from app.modules.mdm.models import Employee
from app.modules.payroll.period_eligibility import employee_on_payroll_period


def _emp(**kwargs) -> Employee:
    return Employee(
        employee_code="9999",
        full_name="Test",
        pay_channel="CASH",
        **kwargs,
    )


def test_resigned_before_period_excluded():
    emp = _emp(
        status="resigned",
        join_date=date(2020, 1, 1),
        resign_date=date(2026, 7, 31),
    )
    assert not employee_on_payroll_period(emp, date(2026, 8, 1), date(2026, 8, 31))


def test_resigned_during_period_included():
    emp = _emp(
        status="resigned",
        join_date=date(2020, 1, 1),
        resign_date=date(2026, 8, 15),
    )
    assert employee_on_payroll_period(emp, date(2026, 8, 1), date(2026, 8, 31))


def test_active_in_period():
    emp = _emp(status="active", join_date=date(2020, 1, 1), resign_date=None)
    assert employee_on_payroll_period(emp, date(2026, 8, 1), date(2026, 8, 31))
