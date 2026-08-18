"""Mẫu Genus phiếu worker — cột CT ngày khi engine chưa ghi quantity."""

from decimal import Decimal

from app.modules.payroll.payslip_genus_template import (
    ALLOWANCE_SLOTS,
    apply_genus_allowance_template,
    fill_ale_leave_quantity,
    fill_missing_day_quantity,
)


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


def test_fill_ale_leave_quantity_from_timesheet():
    lines = [
        {"component_code": "ALE", "amount": None, "quantity": None, "unit": "day"},
        {"component_code": "FLE", "amount": Decimal("1"), "quantity": None, "unit": "day"},
        {"component_code": "ALE", "amount": Decimal("200000"), "quantity": Decimal("1"), "unit": "day"},
    ]
    fill_ale_leave_quantity(lines, Decimal("2"))
    assert lines[0]["quantity"] == Decimal("2")
    assert lines[1]["quantity"] is None
    assert lines[2]["quantity"] == Decimal("1")


def test_allowance_template_splits_pccc_and_hse():
    labels = [s.label for s in ALLOWANCE_SLOTS]
    assert "PCCC" in labels
    assert "HSE" in labels
    assert "PCCC + HSE" not in labels
    lines = apply_genus_allowance_template(
        [
            {
                "component_code": "PCCC",
                "amount": Decimal("882000"),
                "quantity": Decimal("26"),
                "unit": "day",
            },
            {
                "component_code": "HSE",
                "amount": Decimal("50000"),
                "quantity": Decimal("26"),
                "unit": "day",
            },
        ],
        Decimal("26"),
    )
    pccc = next(ln for ln in lines if ln["label"] == "PCCC")
    hse = next(ln for ln in lines if ln["label"] == "HSE")
    assert pccc["amount"] == Decimal("882000")
    assert hse["amount"] == Decimal("50000")
    assert pccc["component_code"] == "PCCC"
    assert hse["component_code"] == "HSE"
