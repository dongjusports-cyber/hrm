"""Calendar service — holidays, work week, divisor preview."""

from __future__ import annotations

from datetime import date, time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.calendar.engine import apply_divisor_rule, count_official_work_days
from app.modules.calendar.models import Holiday, WorkWeekRule
from app.modules.calendar.schemas import (
    DivisorOut,
    HolidayIn,
    HolidayOut,
    WorkWeekOut,
    WorkWeekUpdate,
)
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload


def seed_calendar(db: Session) -> None:
    rule = db.get(WorkWeekRule, 1)
    if rule is None:
        db.add(
            WorkWeekRule(
                id=1,
                work_weekdays=[1, 2, 3, 4, 5, 6],  # T2–T7
                morning_start=time(8, 0),
                morning_end=time(12, 0),
                afternoon_start=time(13, 0),
                afternoon_end=time(17, 0),
                grace_late_minutes=0,
            )
        )
    # Seed lễ mẫu (tránh tháng 9–12/2025 để khớp bảng Excel divisor)
    seeds = [
        (date(2025, 1, 1), "Tết Dương lịch"),
        (date(2025, 4, 30), "Ngày Giải phóng"),
        (date(2025, 5, 1), "Quốc tế Lao động"),
    ]
    for d, name in seeds:
        if db.get(Holiday, d) is None:
            db.add(Holiday(date=d, name=name))
    db.commit()


def get_work_week(db: Session) -> WorkWeekRule:
    rule = db.get(WorkWeekRule, 1)
    if rule is None:
        seed_calendar(db)
        rule = db.get(WorkWeekRule, 1)
    assert rule is not None
    return rule


def update_work_week(db: Session, body: WorkWeekUpdate) -> WorkWeekOut:
    rule = get_work_week(db)
    days = sorted(set(body.work_weekdays))
    for d in days:
        if d < 1 or d > 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trợ Lý AI: ngày trong tuần phải từ 1 (Thứ 2) đến 7 (Chủ nhật).",
            )
    rule.work_weekdays = days
    if body.morning_start is not None:
        rule.morning_start = body.morning_start
    if body.morning_end is not None:
        rule.morning_end = body.morning_end
    if body.afternoon_start is not None:
        rule.afternoon_start = body.afternoon_start
    if body.afternoon_end is not None:
        rule.afternoon_end = body.afternoon_end
    if body.grace_late_minutes is not None:
        rule.grace_late_minutes = body.grace_late_minutes
    db.commit()
    db.refresh(rule)
    return WorkWeekOut.model_validate(rule)


def list_holidays(db: Session, year: int | None = None) -> list[HolidayOut]:
    q = db.query(Holiday).order_by(Holiday.date.asc())
    rows = q.all()
    if year is not None:
        rows = [r for r in rows if r.date.year == year]
    return [HolidayOut.model_validate(r) for r in rows]


def add_holiday(db: Session, body: HolidayIn) -> HolidayOut:
    if db.get(Holiday, body.date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: ngày {body.date.isoformat()} đã có trong lịch lễ.",
        )
    row = Holiday(date=body.date, name=body.name.strip())
    db.add(row)
    db.commit()
    return HolidayOut.model_validate(row)


def delete_holiday(db: Session, day: date) -> None:
    row = db.get(Holiday, day)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy ngày lễ.",
        )
    db.delete(row)
    db.commit()


def _active_divisor_rule(db: Session) -> tuple[dict, str | None]:
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    if pkg and isinstance(pkg.payload, dict):
        rule = pkg.payload.get("divisor_rule") or default_payload()["divisor_rule"]
        return rule, pkg.name
    return default_payload()["divisor_rule"], None


def compute_divisor(db: Session, year: int, month: int) -> DivisorOut:
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: năm không hợp lệ.")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: tháng phải từ 1 đến 12.")

    rule_row = get_work_week(db)
    month_holidays = [
        h for h in db.query(Holiday).all() if h.date.year == year and h.date.month == month
    ]
    holiday_dates = {h.date for h in month_holidays}

    official = count_official_work_days(
        year=year,
        month=month,
        work_weekdays=list(rule_row.work_weekdays),
        holiday_dates=holiday_dates,
    )
    divisor_rule, pkg_name = _active_divisor_rule(db)
    divisor = apply_divisor_rule(official, divisor_rule)

    detail = (
        f"Tháng {month:02d}/{year}: ngày công chuẩn = {official}, "
        f"mẫu số (salary_divisor) = {divisor} "
        f"(rule: khi official={divisor_rule.get('when_official_eq')} → {divisor_rule.get('use_divisor')})."
    )

    return DivisorOut(
        year=year,
        month=month,
        official_work_days=official,
        salary_divisor=divisor,
        divisor_rule=divisor_rule,
        work_weekdays=list(rule_row.work_weekdays),
        holidays_in_month=[HolidayOut.model_validate(h) for h in month_holidays],
        policy_package_name=pkg_name,
        detail=detail,
    )
