"""Migrate mức Chuyên cần / Đi lại sang 600k / 800k."""

from decimal import Decimal

from app.modules.payroll.seed_allowances import (
    ATTEND_MONTHLY_DEFAULT,
    TRANSPORT_MONTHLY_DEFAULT,
    normalize_legacy_allowance_amount,
)


def test_normalize_legacy_attend_transport():
    assert normalize_legacy_allowance_amount("ATTEND", Decimal("230000")) == ATTEND_MONTHLY_DEFAULT
    assert normalize_legacy_allowance_amount("TRANSPORT", Decimal("760000")) == TRANSPORT_MONTHLY_DEFAULT
    assert normalize_legacy_allowance_amount("ATTEND", Decimal("600000")) == Decimal("600000")
    assert normalize_legacy_allowance_amount("TOXIC", Decimal("230000")) == Decimal("230000")
