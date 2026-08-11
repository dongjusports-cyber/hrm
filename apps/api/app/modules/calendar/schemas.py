"""Schemas calendar / divisor."""

from datetime import date, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class HolidayIn(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=200)


class HolidayOut(BaseModel):
    date: date
    name: str

    model_config = {"from_attributes": True}


class WorkWeekOut(BaseModel):
    id: int
    work_weekdays: list[int]
    morning_start: time
    morning_end: time
    afternoon_start: time
    afternoon_end: time
    grace_late_minutes: int

    model_config = {"from_attributes": True}


class WorkWeekUpdate(BaseModel):
    work_weekdays: list[int] = Field(min_length=1, max_length=7)
    morning_start: time | None = None
    morning_end: time | None = None
    afternoon_start: time | None = None
    afternoon_end: time | None = None
    grace_late_minutes: int | None = Field(default=None, ge=0, le=60)


class DivisorOut(BaseModel):
    year: int
    month: int
    official_work_days: Decimal
    salary_divisor: Decimal
    divisor_rule: dict[str, Any]
    work_weekdays: list[int]
    holidays_in_month: list[HolidayOut]
    policy_package_name: str | None
    detail: str
