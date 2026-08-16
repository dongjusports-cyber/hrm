"""Schemas KPI / overview."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.modules.ai.schemas import TodoCardOut


class ManpowerBucket(BaseModel):
    category: str
    label: str
    headcount: int
    ot_hours: Decimal
    worked_days: Decimal


class DeptKpiRow(BaseModel):
    department_code: str
    department_name: str
    category: str
    headcount: int
    worked_days: Decimal
    ot_hours: Decimal
    ot_pay: Decimal


class KpiPeriodOut(BaseModel):
    period: str
    official_work_days: Decimal
    salary_divisor: Decimal
    param_b3: Decimal
    hours_per_day: Decimal
    headcount: int
    begin_hc: int
    recruit: int
    resign: int
    end_hc: int
    attendants: Decimal
    monthly_manpower: Decimal
    attendance_rate: Decimal | None
    attendance_rate_pct: Decimal | None
    ot_hours: Decimal
    reference_hours: Decimal
    ot_rate: Decimal | None
    ot_rate_pct: Decimal | None
    ot_pay_total: Decimal
    turnover_rate: Decimal | None
    turnover_rate_pct: Decimal | None
    open_disputes: int
    by_category: list[ManpowerBucket]
    by_department: list[DeptKpiRow]
    formula_note: str


class OverviewOut(BaseModel):
    period: str
    total_employees: int
    attendance_rate_pct: Decimal | None
    ot_pay_total: Decimal
    open_disputes: int
    ot_hours: Decimal
    turnover_rate_pct: Decimal | None
    recent_alerts: list[dict]
    by_department: list[DeptKpiRow]
    todo_cards: list[TodoCardOut] = []
