"""3.5 — tổng hợp timesheet_month_details theo category × segment (21§21.5)."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.modules.attendance.models import AttendanceDay, TimesheetAdjustment, TimesheetMonthDetail
from app.modules.mdm.models import Employee

ZERO = Decimal("0")
Q2 = Decimal("0.01")
Q4 = Decimal("0.0001")


def _employee_segment(employee: Employee) -> str:
    return "probation" if employee.status == "probation" else "official"


def _hours(minutes: int) -> Decimal:
    if minutes <= 0:
        return ZERO
    return (Decimal(minutes) / Decimal(60)).quantize(Q2, rounding=ROUND_HALF_UP)


def _abs_category(leave_code: str) -> str:
    return f"ABS_{leave_code.strip().upper()}"


def aggregate_month_details(
    day_rows: list[AttendanceDay],
    adj_rows: list[TimesheetAdjustment],
    employee: Employee,
) -> dict[tuple[str, str], dict[str, Decimal]]:
    """{(segment, category): {hours, days}} — chỉ gom số dương."""
    buckets: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(
        lambda: {"hours": ZERO, "days": ZERO}
    )
    fallback_seg = _employee_segment(employee)

    def add(segment: str, category: str, *, hours: Decimal = ZERO, days: Decimal = ZERO) -> None:
        if hours <= 0 and days <= 0:
            return
        key = (segment, category)
        buckets[key]["hours"] += hours
        buckets[key]["days"] += days

    for d in day_rows:
        seg = d.segment or fallback_seg
        if d.leave_code:
            add(seg, _abs_category(d.leave_code), days=Decimal("1"))
        elif d.is_workday and Decimal(d.worked_hours or 0) > 0:
            add(seg, "WT", days=Decimal("1"))

        if (d.ot_on_books_minutes or 0) > 0:
            add(seg, "OT", hours=_hours(d.ot_on_books_minutes))
        if (d.ot_external_minutes or 0) > 0:
            add(seg, "OT_EXT", hours=_hours(d.ot_external_minutes))
        if d.sunday_hours and d.sunday_hours > 0:
            add(seg, "ST", hours=Decimal(d.sunday_hours))
        if d.holiday_hours and d.holiday_hours > 0:
            add(seg, "HT", hours=Decimal(d.holiday_hours))
        if d.ot_night_hours and d.ot_night_hours > 0:
            add(seg, "OT_NIGHT", hours=Decimal(d.ot_night_hours))
        # Ca đêm tắt mặc định — gom vào NT30 khi có dữ liệu (NT45/NT60 bổ sung sau).
        if d.night_hours and d.night_hours > 0:
            add(seg, "NT30", hours=Decimal(d.night_hours))

    adj_seg = fallback_seg
    for a in adj_rows:
        if a.kind == "leave" and a.leave_code and a.days is not None:
            add(adj_seg, _abs_category(a.leave_code), days=Decimal(a.days))
        elif a.kind == "ot" and a.ot_hours is not None and Decimal(a.ot_hours) > 0:
            ot_type = (a.ot_type or "weekday").strip().lower()
            h = Decimal(a.ot_hours).quantize(Q2, rounding=ROUND_HALF_UP)
            if ot_type == "weekend":
                add(adj_seg, "ST", hours=h)
            elif ot_type == "holiday":
                add(adj_seg, "HT", hours=h)
            else:
                add(adj_seg, "OT", hours=h)

    out: dict[tuple[str, str], dict[str, Decimal]] = {}
    for key, vals in buckets.items():
        hours = vals["hours"].quantize(Q2, rounding=ROUND_HALF_UP)
        days = vals["days"].quantize(Q4, rounding=ROUND_HALF_UP).quantize(Q2, rounding=ROUND_HALF_UP)
        if hours > 0 or days > 0:
            out[key] = {"hours": hours, "days": days}
    return out


def sync_timesheet_month_details(
    db: Session,
    timesheet_month_id,
    buckets: dict[tuple[str, str], dict[str, Decimal]],
) -> int:
    """Xóa cũ + ghi mới; trả số dòng detail."""
    db.query(TimesheetMonthDetail).filter(
        TimesheetMonthDetail.timesheet_month_id == timesheet_month_id
    ).delete(synchronize_session=False)
    written = 0
    for (segment, category), vals in sorted(buckets.items()):
        db.add(
            TimesheetMonthDetail(
                timesheet_month_id=timesheet_month_id,
                category=category,
                segment=segment,
                hours=vals["hours"],
                days=vals["days"],
            )
        )
        written += 1
    return written
