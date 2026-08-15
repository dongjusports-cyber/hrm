"""Nạp phiếu lương lịch sử T1–T7/2026 từ salary_by_month trong Dữ liệu công nhân JSON.

Không xóa DB — upsert PayPeriod + TimesheetMonth + Payslip theo MSNV/kỳ.
Dùng sau export_employee_snapshots (GenusSuite đóng băng số liệu).

  python -m app.scripts.import_salary_from_snapshots HIEN_PHAP/Dữ liệu công nhân
  python -m app.scripts.import_salary_from_snapshots ... --dry-run
"""

from __future__ import annotations

import argparse
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip


def _dec(val: Any) -> Decimal:
    if val is None or val == "":
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _period_bounds(year: int, month: int) -> tuple[date, date]:
    date_from = date(year, month, 1)
    date_to = date(year, month, monthrange(year, month)[1])
    return date_from, date_to


def _ensure_period(db: Session, year: int, month: int) -> PayPeriod:
    row = db.query(PayPeriod).filter(PayPeriod.year == year, PayPeriod.month == month).one_or_none()
    if row is not None:
        return row
    date_from, date_to = _period_bounds(year, month)
    row = PayPeriod(
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
        official_work_days=Decimal("26"),
        salary_divisor=Decimal("26"),
        status="published",
    )
    db.add(row)
    db.flush()
    return row


def _upsert_timesheet(db: Session, period: PayPeriod, emp: Employee, rec: dict[str, Any]) -> None:
    row = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == period.id, TimesheetMonth.employee_id == emp.id)
        .one_or_none()
    )
    if row is None:
        row = TimesheetMonth(pay_period_id=period.id, employee_id=emp.id)
        db.add(row)
    row.worked_days = _dec(rec.get("workdays_total"))
    row.al_days = _dec(rec.get("al_days"))
    row.rem_days = _dec(rec.get("rem_days"))
    row.ot_hours_weekday = _dec(rec.get("ot_hours"))


def _upsert_payslip(db: Session, period: PayPeriod, emp: Employee, rec: dict[str, Any]) -> None:
    _, date_to = _period_bounds(period.year, period.month)
    row = (
        db.query(Payslip)
        .filter(Payslip.pay_period_id == period.id, Payslip.employee_id == emp.id)
        .one_or_none()
    )
    if row is None:
        row = Payslip(pay_period_id=period.id, employee_id=emp.id)
        db.add(row)
    row.wd_salary = _dec(rec.get("wd_salary"))
    row.allowance_total = _dec(rec.get("allowance_total"))
    row.ot_pay = _dec(rec.get("ot_pay"))
    row.other_adjustments = Decimal("0")
    row.gross = _dec(rec.get("gross"))
    row.bhxh = _dec(rec.get("bhxh"))
    row.bhyt = _dec(rec.get("bhyt"))
    row.bhtn = _dec(rec.get("bhtn"))
    row.union_fee = _dec(rec.get("union_fee"))
    row.other_deductions = _dec(rec.get("deduct"))
    row.pit_amount = Decimal("0")
    row.net = _dec(rec.get("net"))
    row.status = "confirmed"
    row.confirmed_at = datetime(date_to.year, date_to.month, date_to.day, 12, 0, tzinfo=timezone.utc)
    row.confirm_deadline = date(date_to.year, date_to.month, min(date_to.day, 28))
    row.lines = {
        "source": "GenusSuite JSON snapshot (đóng băng, không qua Payroll Engine)",
        "allowances": {
            "attend": str(_dec(rec.get("allowance_attend"))),
            "position": str(_dec(rec.get("allowance_position"))),
            "toxic": str(_dec(rec.get("allowance_toxic"))),
            "transport": str(_dec(rec.get("allowance_transport"))),
            "pccc_hse": str(_dec(rec.get("allowance_pccc_hse"))),
            "skill": str(_dec(rec.get("allowance_skill"))),
            "seniority": str(_dec(rec.get("allowance_seniority"))),
            "other": str(_dec(rec.get("allowance_other"))),
        },
        "ot_hours": str(_dec(rec.get("ot_hours"))),
        "department_at_period": rec.get("dept"),
    }


def run(snapshot_dir: Path, *, dry_run: bool = False) -> None:
    employees_dir = snapshot_dir / "employees"
    if not employees_dir.is_dir():
        raise FileNotFoundError(f"Không thấy {employees_dir}")

    db = SessionLocal()
    payslips = 0
    skipped_no_emp = 0
    by_month: dict[str, int] = {}
    try:
        for path in sorted(employees_dir.glob("*.json")):
            snap = json.loads(path.read_text(encoding="utf-8"))
            code = snap.get("employee_code") or path.stem
            salary = (snap.get("sources") or {}).get("salary_by_month") or {}
            if not salary:
                continue
            emp = (
                db.query(Employee)
                .filter(Employee.employee_code == code, Employee.deleted_at.is_(None))
                .one_or_none()
            )
            if emp is None:
                skipped_no_emp += 1
                continue
            for period_key, rec in salary.items():
                year_s, month_s = period_key.split("-", 1)
                year, month = int(year_s), int(month_s)
                if dry_run:
                    by_month[period_key] = by_month.get(period_key, 0) + 1
                    payslips += 1
                    continue
                period = _ensure_period(db, year, month)
                _upsert_timesheet(db, period, emp, rec)
                _upsert_payslip(db, period, emp, rec)
                by_month[period_key] = by_month.get(period_key, 0) + 1
                payslips += 1
        if not dry_run:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Phiếu lương: {payslips} | thiếu NV trong DB: {skipped_no_emp}")
    for k in sorted(by_month):
        print(f"  {k}: {by_month[k]} phiếu")
    if dry_run:
        print("DRY-RUN — không ghi DB.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp lương T1–T7 từ JSON salary_by_month")
    parser.add_argument("snapshot_dir", type=Path, help="Thư mục Dữ liệu công nhân")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.snapshot_dir.resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
