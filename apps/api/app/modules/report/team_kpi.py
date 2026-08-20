"""KPI Dongju Sports VN theo tổ + ngày/tháng — chỉ SELECT, không ghi DB.

Nguồn: attendance_days (vân tay). Từ 2026-08-01. OT = ot_minutes (sổ + ngoài + CN + lễ).
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.modules.attendance.models import AttendanceDay
from app.modules.attendance.timesheet import get_pay_period, parse_period
from app.modules.calendar.engine import count_official_work_days, is_official_workday
from app.modules.calendar.models import Holiday, WorkWeekRule
from app.modules.mdm.models import Employee, Team
from app.modules.payroll.money import D, ZERO
from app.modules.payroll.period_eligibility import employee_on_payroll_period
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload
from app.modules.report import engine
from app.modules.report.schemas import (
    KpiDayOut,
    KpiDayPerson,
    KpiMonthDayPoint,
    KpiMonthOut,
    KpiMonthPerson,
    KpiTeamDayCell,
    KpiTeamDayRow,
    KpiTeamMonthRow,
)

KPI_FROM = date(2026, 8, 1)
UNASSIGNED_TEAM_ID = "unassigned"
Q2 = Decimal("0.01")
CAT_LABELS = {
    "direct": "Trực tiếp",
    "prod_indirect": "Gián tiếp SX",
    "admin_indirect": "Gián tiếp VP",
}


def require_kpi_from_date(d: date) -> None:
    if d < KPI_FROM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Trợ Lý AI: KPI Dongju Sports VN lấy từ DJ-HRM từ tháng 8/2026. "
                "Tháng trước không có dữ liệu trên Portal."
            ),
        )


def require_kpi_from_period(period: str) -> tuple[int, int]:
    year, month = parse_period(period)
    require_kpi_from_date(date(year, month, 1))
    return year, month


def _hours(minutes: int) -> Decimal:
    if minutes <= 0:
        return ZERO
    return (Decimal(minutes) / Decimal(60)).quantize(Q2, rounding=ROUND_HALF_UP)


def _active_payload(db: Session) -> dict:
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        return dict(pkg.payload)
    return default_payload()


def _b3_hours(db: Session, official_work_days: Decimal) -> tuple[Decimal, Decimal]:
    payload = _active_payload(db)
    raw = payload.get("kpi_manpower_factor")
    b3 = D(raw) if raw is not None else D(official_work_days)
    if b3 <= 0:
        b3 = D(official_work_days) if official_work_days else D(26)
    hours = D(payload.get("kpi_hours_per_day") or 8)
    if hours <= 0:
        hours = D(8)
    return b3, hours


def _work_calendar(db: Session, year: int, month: int) -> tuple[list[int], set[date], Decimal]:
    rule = db.get(WorkWeekRule, 1)
    weekdays = list(rule.work_weekdays) if rule and rule.work_weekdays else [1, 2, 3, 4, 5, 6]
    holidays = {
        h.date
        for h in db.query(Holiday).all()
        if h.date.year == year and h.date.month == month
    }
    pay = get_pay_period(db, f"{year:04d}-{month:02d}")
    if pay is not None and pay.official_work_days:
        official = D(pay.official_work_days)
    else:
        official = count_official_work_days(
            year=year, month=month, work_weekdays=weekdays, holiday_dates=holidays
        )
    return weekdays, holidays, official


def _on_payroll_day(emp: Employee, day: date) -> bool:
    if emp.deleted_at is not None:
        return False
    if emp.join_date and emp.join_date > day:
        return False
    if emp.resign_date and emp.resign_date < day:
        return False
    if emp.status == "resigned" and emp.resign_date is None:
        return False
    return True


def _load_employees(db: Session) -> list[Employee]:
    return (
        db.query(Employee)
        .options(joinedload(Employee.team).joinedload(Team.department))
        .filter(Employee.deleted_at.is_(None))
        .all()
    )


def _team_meta(emp: Employee) -> tuple[str, str, str, str, str, str, int, int]:
    team = emp.team
    if team is None:
        return UNASSIGNED_TEAM_ID, "—", "Chưa gán tổ", "—", "Chưa gán bộ phận", "direct", 9_999, 9_999
    dept = team.department
    cat = dept.category if dept and dept.category in CAT_LABELS else "direct"
    dept_code = dept.code if dept else "—"
    dept_name = dept.name if dept else "Chưa gán bộ phận"
    d_sort = dept.sort_order if dept else 9_999
    return (
        str(team.id),
        team.code,
        team.name,
        dept_code,
        dept_name,
        cat,
        d_sort,
        team.sort_order,
    )


def _is_present(day: AttendanceDay | None) -> bool:
    if day is None:
        return False
    return int(day.punch_count or 0) > 0 or day.first_in is not None


def _ot_minutes(day: AttendanceDay | None) -> int:
    if day is None:
        return 0
    return max(0, int(day.ot_minutes or 0))


def company_day_summary(rows: list[KpiTeamDayRow]) -> dict:
    hc = sum(r.headcount for r in rows)
    present = sum(r.present for r in rows)
    ot_people = sum(r.ot_people for r in rows)
    ot_hours = sum((r.ot_hours for r in rows), ZERO)
    teams_ot = sum(1 for r in rows if r.ot_people > 0)
    missing = sum(r.missing_punch for r in rows)
    late = sum(r.late_people for r in rows)
    return {
        "headcount": hc,
        "present": present,
        "absent": max(0, hc - present),
        "teams_with_ot": teams_ot,
        "ot_people": ot_people,
        "ot_hours": ot_hours,
        "missing_punch": missing,
        "late_people": late,
    }


def compute_day(db: Session, work_date: date) -> KpiDayOut:
    require_kpi_from_date(work_date)
    weekdays, holidays, _official = _work_calendar(db, work_date.year, work_date.month)
    is_work = is_official_workday(work_date, weekdays, holidays)
    emps = [e for e in _load_employees(db) if _on_payroll_day(e, work_date)]
    ids = [e.id for e in emps]
    day_by_emp: dict[UUID, AttendanceDay] = {}
    if ids:
        for row in db.query(AttendanceDay).filter(
            AttendanceDay.work_date == work_date,
            AttendanceDay.employee_id.in_(ids),
        ):
            day_by_emp[row.employee_id] = row

    buckets: dict[str, dict] = {}
    for emp in emps:
        tid, tcode, tname, dcode, dname, cat, ds, ts = _team_meta(emp)
        if tid not in buckets:
            buckets[tid] = {
                "team_id": tid,
                "team_code": tcode,
                "team_name": tname,
                "department_code": dcode,
                "department_name": dname,
                "category": cat,
                "d_sort": ds,
                "t_sort": ts,
                "hc": 0,
                "present": 0,
                "ot_people": 0,
                "ot_min": 0,
                "ot_books": 0,
                "ot_ext": 0,
                "late": 0,
                "missing": 0,
            }
        b = buckets[tid]
        b["hc"] += 1
        ad = day_by_emp.get(emp.id)
        present = _is_present(ad)
        if present:
            b["present"] += 1
        otm = _ot_minutes(ad)
        if otm > 0:
            b["ot_people"] += 1
            b["ot_min"] += otm
            if ad is not None:
                b["ot_books"] += max(0, int(ad.ot_on_books_minutes or 0))
                b["ot_ext"] += max(0, int(ad.ot_external_minutes or 0))
        if ad is not None and int(ad.late_minutes or 0) > 0:
            b["late"] += 1
        workday_emp = bool(ad.is_workday) if ad is not None else is_work
        if workday_emp and not present and not (ad and ad.leave_code):
            b["missing"] += 1

    ranked: list[tuple[tuple, KpiTeamDayRow]] = []
    for b in buckets.values():
        ot_h = _hours(b["ot_min"])
        avg = (ot_h / D(b["ot_people"])).quantize(Q2, rounding=ROUND_HALF_UP) if b["ot_people"] else ZERO
        ranked.append(
            (
                (b["d_sort"], b["t_sort"], b["team_name"]),
                KpiTeamDayRow(
                    team_id=b["team_id"],
                    team_code=b["team_code"],
                    team_name=b["team_name"],
                    department_code=b["department_code"],
                    department_name=b["department_name"],
                    category=b["category"],
                    category_label=CAT_LABELS.get(b["category"], b["category"]),
                    headcount=b["hc"],
                    present=b["present"],
                    absent=max(0, b["hc"] - b["present"]),
                    missing_punch=b["missing"],
                    late_people=b["late"],
                    ot_people=b["ot_people"],
                    ot_hours=ot_h,
                    ot_on_books_hours=_hours(b["ot_books"]),
                    ot_external_hours=_hours(b["ot_ext"]),
                    ot_hours_per_person=avg,
                ),
            )
        )
    ranked.sort(key=lambda x: x[0])
    clean = [row for _k, row in ranked]
    totals = company_day_summary(clean)
    return KpiDayOut(
        work_date=work_date.isoformat(),
        is_workday=is_work,
        source="attendance_days",
        formula_note=(
            "Có mặt = có vân tay. OT = ot_minutes (sổ + ngoài + CN + lễ). "
            "Vắng = HC − có mặt. Thiếu chấm = ngày công, không vân tay, không mã nghỉ."
        ),
        **totals,
        teams=clean,
    )


def list_day_people(db: Session, work_date: date, team_id: str | None = None) -> list[KpiDayPerson]:
    require_kpi_from_date(work_date)
    emps = [e for e in _load_employees(db) if _on_payroll_day(e, work_date)]
    if team_id == UNASSIGNED_TEAM_ID:
        emps = [e for e in emps if e.team_id is None]
    elif team_id:
        try:
            tid = UUID(team_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: team_id không hợp lệ.",
            ) from exc
        emps = [e for e in emps if e.team_id == tid]
    ids = [e.id for e in emps]
    day_by_emp: dict[UUID, AttendanceDay] = {}
    if ids:
        for row in db.query(AttendanceDay).filter(
            AttendanceDay.work_date == work_date,
            AttendanceDay.employee_id.in_(ids),
        ):
            day_by_emp[row.employee_id] = row
    out: list[KpiDayPerson] = []
    for emp in emps:
        ad = day_by_emp.get(emp.id)
        tid, tcode, tname, dcode, dname, _cat, _ds, _ts = _team_meta(emp)
        otm = _ot_minutes(ad)
        out.append(
            KpiDayPerson(
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                team_id=tid,
                team_code=tcode,
                team_name=tname,
                department_code=dcode,
                department_name=dname,
                present=_is_present(ad),
                punch_count=int(ad.punch_count or 0) if ad else 0,
                first_in=ad.first_in.isoformat() if ad and ad.first_in else None,
                last_out=ad.last_out.isoformat() if ad and ad.last_out else None,
                worked_hours=D(ad.worked_hours) if ad else ZERO,
                late_minutes=int(ad.late_minutes or 0) if ad else 0,
                early_minutes=int(ad.early_minutes or 0) if ad else 0,
                leave_code=ad.leave_code if ad else None,
                ot_hours=_hours(otm),
                ot_on_books_hours=_hours(int(ad.ot_on_books_minutes or 0) if ad else 0),
                ot_external_hours=_hours(int(ad.ot_external_minutes or 0) if ad else 0),
            )
        )
    out.sort(key=lambda p: (-float(p.ot_hours), 0 if p.present else 1, p.employee_code))
    return out


def compute_month(db: Session, period: str) -> KpiMonthOut:
    year, month = require_kpi_from_period(period)
    last = calendar.monthrange(year, month)[1]
    start, end = date(year, month, 1), date(year, month, last)
    weekdays, holidays, official = _work_calendar(db, year, month)
    b3, hours_day = _b3_hours(db, official)
    dates = [date(year, month, d) for d in range(1, last + 1)]
    workday_set = {d for d in dates if is_official_workday(d, weekdays, holidays)}

    emps = [e for e in _load_employees(db) if employee_on_payroll_period(e, start, end)]
    ids = [e.id for e in emps]
    days_by_emp: dict[UUID, dict[date, AttendanceDay]] = defaultdict(dict)
    if ids:
        for row in db.query(AttendanceDay).filter(
            AttendanceDay.employee_id.in_(ids),
            AttendanceDay.work_date >= start,
            AttendanceDay.work_date <= end,
        ):
            days_by_emp[row.employee_id][row.work_date] = row

    buckets: dict[str, dict] = {}
    for emp in emps:
        tid, tcode, tname, dcode, dname, cat, ds, ts = _team_meta(emp)
        if tid not in buckets:
            buckets[tid] = {
                "team_id": tid,
                "team_code": tcode,
                "team_name": tname,
                "department_code": dcode,
                "department_name": dname,
                "category": cat,
                "d_sort": ds,
                "t_sort": ts,
                "hc": 0,
                "begin": 0,
                "recruit": 0,
                "resign": 0,
                "hc_by_day": defaultdict(int),
                "present_by_day": defaultdict(int),
                "ot_min_by_day": defaultdict(int),
                "ot_people_by_day": defaultdict(set),
                "ot_people_month": set(),
                "ot_min": 0,
            }
        b = buckets[tid]
        b["hc"] += 1
        if emp.join_date is None or emp.join_date < start:
            if emp.resign_date is None or emp.resign_date >= start:
                b["begin"] += 1
        if emp.join_date and start <= emp.join_date <= end:
            b["recruit"] += 1
        if emp.resign_date and start <= emp.resign_date <= end:
            b["resign"] += 1
        for day in dates:
            if not _on_payroll_day(emp, day):
                continue
            b["hc_by_day"][day] += 1
            ad = days_by_emp[emp.id].get(day)
            if _is_present(ad):
                b["present_by_day"][day] += 1
            otm = _ot_minutes(ad)
            if otm > 0:
                b["ot_min_by_day"][day] += otm
                b["ot_people_by_day"][day].add(emp.employee_code)
                b["ot_people_month"].add(emp.employee_code)
                b["ot_min"] += otm

    ranked_m: list[tuple[tuple, KpiTeamMonthRow]] = []
    for b in buckets.values():
        cells = []
        attendants = ZERO
        for day in dates:
            present = int(b["present_by_day"][day])
            ot_h = _hours(int(b["ot_min_by_day"][day]))
            ot_p = len(b["ot_people_by_day"][day])
            attendants += D(present)
            cells.append(
                KpiTeamDayCell(
                    work_date=day.isoformat(),
                    is_workday=day in workday_set,
                    present=present,
                    ot_hours=ot_h,
                    ot_people=ot_p,
                )
            )
        end_hc = engine.end_headcount(b["begin"], b["recruit"], b["resign"])
        manpower = engine.monthly_manpower(b["hc"], b3)
        att_rate = engine.attendance_rate(attendants, manpower)
        ot_h = _hours(b["ot_min"])
        actual_wh = attendants * hours_day
        ref_h = engine.reference_hours(b["hc"], official, hours_day)
        share = engine.ot_rate(ot_h, ot_h + actual_wh) if (ot_h + actual_wh) > 0 else None
        cap = engine.ot_rate(ot_h, ref_h)
        t_rate = engine.turnover_rate(b["resign"], b["begin"], end_hc)
        ranked_m.append(
            (
                (b["d_sort"], b["t_sort"], b["team_name"]),
                KpiTeamMonthRow(
                    team_id=b["team_id"],
                    team_code=b["team_code"],
                    team_name=b["team_name"],
                    department_code=b["department_code"],
                    department_name=b["department_name"],
                    category=b["category"],
                    category_label=CAT_LABELS.get(b["category"], b["category"]),
                    headcount=b["hc"],
                    begin_hc=b["begin"],
                    recruit=b["recruit"],
                    resign=b["resign"],
                    end_hc=end_hc,
                    attendants=attendants,
                    monthly_manpower=manpower,
                    attendance_rate=att_rate,
                    attendance_rate_pct=engine.pct(att_rate),
                    ot_hours=ot_h,
                    ot_people=len(b["ot_people_month"]),
                    actual_work_hours=actual_wh,
                    ot_share_rate=share,
                    ot_share_pct=engine.pct(share),
                    ot_capacity_rate=cap,
                    ot_capacity_pct=engine.pct(cap),
                    turnover_rate=t_rate,
                    turnover_rate_pct=engine.pct(t_rate),
                    days=cells,
                ),
            )
        )
    ranked_m.sort(key=lambda x: x[0])
    clean = [row for _k, row in ranked_m]

    company_days: list[KpiMonthDayPoint] = []
    for day in dates:
        hc = sum(int(b["hc_by_day"][day]) for b in buckets.values())
        present = sum(int(b["present_by_day"][day]) for b in buckets.values())
        ot_min = sum(int(b["ot_min_by_day"][day]) for b in buckets.values())
        ot_codes: set[str] = set()
        for b in buckets.values():
            ot_codes |= b["ot_people_by_day"][day]
        company_days.append(
            KpiMonthDayPoint(
                work_date=day.isoformat(),
                is_workday=day in workday_set,
                headcount=hc,
                present=present,
                absent=max(0, hc - present),
                ot_hours=_hours(ot_min),
                ot_people=len(ot_codes),
            )
        )

    tot_hc = sum(r.headcount for r in clean)
    tot_att = sum((r.attendants for r in clean), ZERO)
    tot_ot = sum((r.ot_hours for r in clean), ZERO)
    tot_ot_people = sum(r.ot_people for r in clean)
    tot_begin = sum(r.begin_hc for r in clean)
    tot_in = sum(r.recruit for r in clean)
    tot_out = sum(r.resign for r in clean)
    tot_end = engine.end_headcount(tot_begin, tot_in, tot_out)
    manpower = engine.monthly_manpower(tot_hc, b3)
    att_rate = engine.attendance_rate(tot_att, manpower)
    actual_wh = tot_att * hours_day
    ref_h = engine.reference_hours(tot_hc, official, hours_day)
    share = engine.ot_rate(tot_ot, tot_ot + actual_wh) if (tot_ot + actual_wh) > 0 else None
    cap = engine.ot_rate(tot_ot, ref_h)
    t_rate = engine.turnover_rate(tot_out, tot_begin, tot_end)
    return KpiMonthOut(
        period=period,
        date_from=start.isoformat(),
        date_to=end.isoformat(),
        official_work_days=official,
        param_b3=b3,
        hours_per_day=hours_day,
        headcount=tot_hc,
        begin_hc=tot_begin,
        recruit=tot_in,
        resign=tot_out,
        end_hc=tot_end,
        attendants=tot_att,
        monthly_manpower=manpower,
        attendance_rate=att_rate,
        attendance_rate_pct=engine.pct(att_rate),
        ot_hours=tot_ot,
        ot_people=tot_ot_people,
        actual_work_hours=actual_wh,
        ot_share_rate=share,
        ot_share_pct=engine.pct(share),
        ot_capacity_rate=cap,
        ot_capacity_pct=engine.pct(cap),
        reference_hours=ref_h,
        turnover_rate=t_rate,
        turnover_rate_pct=engine.pct(t_rate),
        source="attendance_days",
        formula_note=(
            "Chuyên cần = tổng ngày có mặt ÷ (HC × B3). "
            "Tỷ lệ OT (chia sẻ) = OT ÷ (OT + ngày có mặt × 8h) — công thức file HQ. "
            "Tỷ lệ OT (công suất) = OT ÷ (HC × ngày công × 8h). "
            "OT = ot_minutes. Từ tháng 8/2026."
        ),
        days=company_days,
        teams=clean,
    )


def list_month_people(db: Session, period: str, team_id: str | None = None) -> list[KpiMonthPerson]:
    year, month = require_kpi_from_period(period)
    last = calendar.monthrange(year, month)[1]
    start, end = date(year, month, 1), date(year, month, last)
    emps = [e for e in _load_employees(db) if employee_on_payroll_period(e, start, end)]
    if team_id == UNASSIGNED_TEAM_ID:
        emps = [e for e in emps if e.team_id is None]
    elif team_id:
        try:
            tid = UUID(team_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: team_id không hợp lệ.",
            ) from exc
        emps = [e for e in emps if e.team_id == tid]
    ids = [e.id for e in emps]
    days_by_emp: dict[UUID, list[AttendanceDay]] = defaultdict(list)
    if ids:
        for row in db.query(AttendanceDay).filter(
            AttendanceDay.employee_id.in_(ids),
            AttendanceDay.work_date >= start,
            AttendanceDay.work_date <= end,
        ):
            days_by_emp[row.employee_id].append(row)
    out: list[KpiMonthPerson] = []
    for emp in emps:
        tid, tcode, tname, dcode, dname, _cat, _ds, _ts = _team_meta(emp)
        present_days = 0
        ot_min = 0
        late_days = 0
        for ad in days_by_emp[emp.id]:
            if _is_present(ad):
                present_days += 1
            ot_min += _ot_minutes(ad)
            if int(ad.late_minutes or 0) > 0:
                late_days += 1
        out.append(
            KpiMonthPerson(
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                team_id=tid,
                team_code=tcode,
                team_name=tname,
                department_code=dcode,
                department_name=dname,
                present_days=present_days,
                late_days=late_days,
                ot_hours=_hours(ot_min),
            )
        )
    out.sort(key=lambda p: (-float(p.ot_hours), -p.present_days, p.employee_code))
    return out
