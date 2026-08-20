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


class KpiTeamDayRow(BaseModel):
    team_id: str
    team_code: str
    team_name: str
    department_code: str
    department_name: str
    category: str
    category_label: str
    headcount: int
    present: int
    absent: int
    missing_punch: int
    late_people: int
    ot_people: int
    ot_hours: Decimal
    ot_on_books_hours: Decimal
    ot_external_hours: Decimal
    ot_hours_per_person: Decimal


class KpiDayOut(BaseModel):
    work_date: str
    is_workday: bool
    source: str
    formula_note: str
    headcount: int
    present: int
    absent: int
    teams_with_ot: int
    ot_people: int
    ot_hours: Decimal
    missing_punch: int
    late_people: int
    teams: list[KpiTeamDayRow]


class KpiDayPerson(BaseModel):
    employee_code: str
    full_name: str
    team_id: str
    team_code: str
    team_name: str
    department_code: str
    department_name: str
    present: bool
    punch_count: int
    first_in: str | None
    last_out: str | None
    worked_hours: Decimal
    late_minutes: int
    early_minutes: int
    leave_code: str | None
    ot_hours: Decimal
    ot_on_books_hours: Decimal
    ot_external_hours: Decimal


class KpiTeamDayCell(BaseModel):
    work_date: str
    is_workday: bool
    present: int
    ot_hours: Decimal
    ot_people: int


class KpiTeamMonthRow(BaseModel):
    team_id: str
    team_code: str
    team_name: str
    department_code: str
    department_name: str
    category: str
    category_label: str
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
    ot_people: int
    actual_work_hours: Decimal
    ot_share_rate: Decimal | None
    ot_share_pct: Decimal | None
    ot_capacity_rate: Decimal | None
    ot_capacity_pct: Decimal | None
    turnover_rate: Decimal | None
    turnover_rate_pct: Decimal | None
    days: list[KpiTeamDayCell]


class KpiMonthOut(BaseModel):
    period: str
    date_from: str
    date_to: str
    official_work_days: Decimal
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
    ot_people: int
    actual_work_hours: Decimal
    ot_share_rate: Decimal | None
    ot_share_pct: Decimal | None
    ot_capacity_rate: Decimal | None
    ot_capacity_pct: Decimal | None
    reference_hours: Decimal
    turnover_rate: Decimal | None
    turnover_rate_pct: Decimal | None
    source: str
    formula_note: str
    teams: list[KpiTeamMonthRow]


class KpiMonthPerson(BaseModel):
    employee_code: str
    full_name: str
    team_id: str
    team_code: str
    team_name: str
    department_code: str
    department_name: str
    present_days: int
    late_days: int
    ot_hours: Decimal
