"""Mẫu Genus phiếu worker — cột CT ngày khi engine chưa ghi quantity."""

from decimal import Decimal

from app.modules.payroll.payslip_genus_template import fill_missing_day_quantity


def test_fill_missing_day_quantity_only_when_amount():
    lines = [
        {"amount": Decimal("100000"), "unit": "day", "quantity": None},
        {"amount": None, "unit": "day", "quantity": None},
        {"amount": Decimal("50000"), "unit": "day", "quantity": Decimal("20")},
        {"amount": Decimal("10000"), "unit": "hour", "quantity": None},
    ]
    fill_missing_day_quantity(lines, Decimal("23.04"))
    assert lines[0]["quantity"] == Decimal("23.04")
    assert lines[1]["quantity"] is None
    assert lines[2]["quantity"] == Decimal("20")
    assert lines[3]["quantity"] is None


def test_fill_missing_day_quantity_noop_when_no_days():
    lines = [{"amount": Decimal("1"), "unit": "day", "quantity": None}]
    fill_missing_day_quantity(lines, None)
    assert lines[0]["quantity"] is None
