"""Schemas OT ngoài — preview API."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class OtExternalPayRowOut(BaseModel):
    employee_code: str
    full_name: str
    bank_account: str
    raw_hours: Decimal
    effective_hours: Decimal
    ot_base: Decimal
    hourly_base: Decimal
    rate: Decimal
    amount_vnd: Decimal
    hours_x15: Decimal = Decimal("0")
    pay_x15: Decimal = Decimal("0")
    hours_x21: Decimal = Decimal("0")
    pay_x21: Decimal = Decimal("0")
    hours_x20: Decimal = Decimal("0")
    pay_x20: Decimal = Decimal("0")
    hours_x35: Decimal = Decimal("0")
    pay_x35: Decimal = Decimal("0")
    hours_x41: Decimal = Decimal("0")
    pay_x41: Decimal = Decimal("0")
    hours_x30: Decimal = Decimal("0")
    pay_x30: Decimal = Decimal("0")
    hours_x45: Decimal = Decimal("0")
    pay_x45: Decimal = Decimal("0")
    hours_x51: Decimal = Decimal("0")
    pay_x51: Decimal = Decimal("0")


class OtExternalSummaryOut(BaseModel):
    period: str
    employee_count: int
    total_raw_hours: Decimal
    total_effective_hours: Decimal
    total_amount_vnd: Decimal
    policy_note: str
    rows: list[OtExternalPayRowOut]
