"""Định dạng ngày chuẩn DJ HRM — dd/mm/yyyy."""

from __future__ import annotations

from datetime import date, datetime


def format_date_vn(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")


def format_datetime_vn(value: datetime | None) -> str:
    if value is None:
        return ""
    return f"{format_date_vn(value.date())} {value.strftime('%H:%M')}"
