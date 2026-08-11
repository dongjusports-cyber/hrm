"""
4.4 — Phạt chuyên cần F_CAL_INDUS_AMT (22§22.3).

- Trễ/sớm: ngưỡng độc lập (late_half/early_half → 50%, late_zero/early_zero/vắng → 0%)
- Miễn trừ trễ/sớm: ALE/FLE/WED + giờ nghỉ < 8 + có chấm vân tay + P_IN <= P_OUT
- Vắng: mã không thuộc ALE/FLE/WED/TMP/OFF, sau hết thử việc
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.modules.payroll.money import D, ZERO

_ABSENCE_EXEMPT_DEFAULT = frozenset({"ALE", "FLE", "WED", "TMP", "OFF"})
_STANDARD_DAY_HOURS = Decimal("8")


@dataclass(frozen=True)
class AttendanceDayPenaltyView:
    work_date: date
    is_workday: bool
    leave_code: str | None
    late_minutes: int
    early_minutes: int
    punch_count: int
    first_in: datetime | None
    last_out: datetime | None
    worked_hours: Decimal


@dataclass(frozen=True)
class LeaveAdjustmentView:
    leave_code: str
    days: Decimal


@dataclass(frozen=True)
class AttendancePenaltySummary:
    late_count: int
    early_count: int
    penalty_absent_days: Decimal
    raw_late_count: int
    raw_early_count: int
    exempt_late_days: int
    exempt_early_days: int
    detail: dict[str, Any]


def day_leave_hours(day: AttendanceDayPenaltyView, *, full_day_hours: Decimal = _STANDARD_DAY_HOURS) -> Decimal:
    if not day.leave_code:
        return ZERO
    worked = D(day.worked_hours)
    if worked >= full_day_hours:
        return ZERO
    return max(ZERO, full_day_hours - worked)


def is_late_early_exempt(day: AttendanceDayPenaltyView, penalties: dict[str, Any]) -> bool:
    codes = {str(c).strip().upper() for c in (penalties.get("exempt_leave_codes") or ["ALE", "FLE", "WED"])}
    code = (day.leave_code or "").strip().upper()
    if not code or code not in codes:
        return False

    hours_lt = D(penalties.get("exempt_requires_hours_lt", 8))
    if day_leave_hours(day) >= hours_lt:
        return False

    if penalties.get("exempt_requires_punch", True):
        if day.punch_count <= 0:
            return False
        if day.first_in is None or day.last_out is None:
            return False
        if day.first_in > day.last_out:
            return False
    return True


def _after_probation(work_date: date, contract_signed_at: date | None, penalties: dict[str, Any]) -> bool:
    if not penalties.get("ignore_absence_during_probation", True):
        return True
    if contract_signed_at is None:
        return True
    return work_date >= contract_signed_at


def is_penalty_absence_day(
    day: AttendanceDayPenaltyView,
    *,
    contract_signed_at: date | None,
    penalties: dict[str, Any],
) -> bool:
    if not day.is_workday:
        return False
    if not _after_probation(day.work_date, contract_signed_at, penalties):
        return False
    code = (day.leave_code or "").strip().upper()
    if not code:
        return False
    exempt = {str(c).strip().upper() for c in penalties.get("absence_exempt_leave_codes") or _ABSENCE_EXEMPT_DEFAULT}
    return code not in exempt


def summarize_attendance_penalties(
    days: list[AttendanceDayPenaltyView],
    adjustments: list[LeaveAdjustmentView],
    *,
    contract_signed_at: date | None,
    penalties: dict[str, Any],
) -> AttendancePenaltySummary:
    raw_late = 0
    raw_early = 0
    exempt_late = 0
    exempt_early = 0
    late = 0
    early = 0

    for day in days:
        if day.late_minutes > 0:
            raw_late += 1
            if is_late_early_exempt(day, penalties):
                exempt_late += 1
            else:
                late += 1
        if day.early_minutes > 0:
            raw_early += 1
            if is_late_early_exempt(day, penalties):
                exempt_early += 1
            else:
                early += 1

    absent = ZERO
    absent_days_detail: list[dict[str, str]] = []
    for day in days:
        if is_penalty_absence_day(day, contract_signed_at=contract_signed_at, penalties=penalties):
            absent += Decimal("1")
            absent_days_detail.append({"date": day.work_date.isoformat(), "leave_code": day.leave_code or ""})

    penalty_adj_codes = {
        str(c).strip().upper() for c in (penalties.get("penalty_leave_codes") or ["NOP", "NON"])
    }
    adj_detail: list[dict[str, str]] = []
    for adj in adjustments:
        code = adj.leave_code.strip().upper()
        if code not in penalty_adj_codes:
            continue
        if adj.days <= 0:
            continue
        absent += D(adj.days)
        adj_detail.append({"leave_code": code, "days": str(adj.days)})

    return AttendancePenaltySummary(
        late_count=late,
        early_count=early,
        penalty_absent_days=absent,
        raw_late_count=raw_late,
        raw_early_count=raw_early,
        exempt_late_days=exempt_late,
        exempt_early_days=exempt_early,
        detail={
            "formula": "F_CAL_INDUS_AMT",
            "raw_late_count": raw_late,
            "raw_early_count": raw_early,
            "exempt_late_days": exempt_late,
            "exempt_early_days": exempt_early,
            "effective_late_count": late,
            "effective_early_count": early,
            "penalty_absent_days": str(absent),
            "absence_days": absent_days_detail,
            "adjustment_absences": adj_detail,
        },
    )
