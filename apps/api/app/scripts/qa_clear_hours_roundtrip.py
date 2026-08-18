"""QA local: xóa giờ → nhập mới → xóa lại. Khôi phục giờ gốc khi xong.

Chạy trong container API, ghi DB Docker local. Không đụng VPS.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.attendance.day_grid import patch_day_cell
from app.modules.attendance.models import AttendanceDay, TimesheetMonth
from app.modules.attendance.service import list_days
from app.modules.attendance.timesheet import ensure_pay_period
from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.payroll.service import _active_policy, compute_employee_payslip

CODE = os.environ.get("QA_EMP", "1520")
DAY = date.fromisoformat(os.environ.get("QA_DAY", "2026-08-18"))
PERIOD = f"{DAY.year:04d}-{DAY.month:02d}"


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def main() -> None:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.username.in_(("hr.demo", "admin")), User.is_active.is_(True))
            .order_by(User.username.desc())
            .first()
        )
        if user is None:
            user = db.query(User).filter(User.is_active.is_(True)).first()
        if user is None:
            raise SystemExit("Khong co user de ghi audit")
        emp = (
            db.query(Employee)
            .filter(Employee.employee_code == CODE, Employee.deleted_at.is_(None))
            .one_or_none()
        )
        if emp is None:
            raise SystemExit(f"Khong thay MSNV {CODE}")
        pay = ensure_pay_period(db, PERIOD)
        if pay.status == "locked":
            raise SystemExit(f"Ky {PERIOD} dang khoa — khong sua cong")

        def day_row() -> dict:
            listed = list_days(db, DAY, DAY, CODE)
            if not listed:
                return {}
            r = listed[0]
            return {
                "first_in": r.first_in.isoformat() if r.first_in else None,
                "last_out": r.last_out.isoformat() if r.last_out else None,
                "worked_hours": str(r.worked_hours),
                "source": r.source,
                "note": r.note,
            }

        def ts_days() -> Decimal:
            ts = (
                db.query(TimesheetMonth)
                .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
                .one_or_none()
            )
            return _d(ts.worked_days if ts else 0)

        def wd_salary() -> Decimal:
            ts = (
                db.query(TimesheetMonth)
                .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
                .one()
            )
            _pkg, payload = _active_policy(db)
            calc = compute_employee_payslip(db, pay, emp, ts, payload)
            return _d(calc.wd_salary)

        snap = day_row()
        orig_in = snap.get("first_in")
        orig_out = snap.get("last_out")
        orig_note = snap.get("note") or ""
        orig_hours = _d(snap.get("worked_hours"))
        steps = []

        def rec(label: str, row: dict) -> None:
            steps.append(
                {
                    "buoc": label,
                    "vao": row.get("first_in"),
                    "ra": row.get("last_out"),
                    "gio_cong": row.get("worked_hours"),
                    "cham_cong_ngay": str(ts_days()),
                    "luong_thu_wd": str(wd_salary()),
                }
            )

        rec("goc", snap)

        patch_day_cell(
            db, user, employee_code=CODE, work_date=DAY, clear_times=True, note="QA xoa gio"
        )
        rec("xoa_gio", day_row())

        patch_day_cell(
            db,
            user,
            employee_code=CODE,
            work_date=DAY,
            first_in=datetime.fromisoformat(f"{DAY.isoformat()}T07:30:00+07:00"),
            last_out=datetime.fromisoformat(f"{DAY.isoformat()}T17:00:00+07:00"),
            note="QA nhap gio moi",
        )
        rec("nhap_gio_moi", day_row())

        patch_day_cell(db, user, employee_code=CODE, work_date=DAY, clear_times=True, note="QA xoa gio moi")
        rec("xoa_gio_moi", day_row())

        if orig_in or orig_out:
            patch_day_cell(
                db,
                user,
                employee_code=CODE,
                work_date=DAY,
                first_in=datetime.fromisoformat(orig_in) if orig_in else None,
                last_out=datetime.fromisoformat(orig_out) if orig_out else None,
                clear_first_in=not orig_in,
                clear_last_out=not orig_out,
                note=orig_note or "QA khoi phuc",
            )
        else:
            patch_day_cell(
                db, user, employee_code=CODE, work_date=DAY, clear_times=True, note=orig_note
            )
        rec("khoi_phuc", day_row())

        d_goc = _d(steps[0]["cham_cong_ngay"])
        d_xoa = _d(steps[1]["cham_cong_ngay"])
        d_moi = _d(steps[2]["cham_cong_ngay"])
        d_xoa2 = _d(steps[3]["cham_cong_ngay"])
        wd_goc = _d(steps[0]["luong_thu_wd"])
        wd_xoa = _d(steps[1]["luong_thu_wd"])
        wd_moi = _d(steps[2]["luong_thu_wd"])
        wd_xoa2 = _d(steps[3]["luong_thu_wd"])
        checks = {
            "xoa_gio_ve_0": _d(steps[1]["gio_cong"]) == 0,
            "cham_cong_giam_khi_xoa": d_xoa < d_goc if orig_hours > 0 else d_xoa == d_goc,
            "nhap_moi_8h": _d(steps[2]["gio_cong"]) == Decimal("8"),
            "cham_cong_tang_khi_nhap": d_moi > d_xoa,
            "xoa_moi_ve_0": _d(steps[3]["gio_cong"]) == 0,
            "cham_cong_sau_xoa_moi_bang_sau_xoa_dau": d_xoa2 == d_xoa,
            "luong_thu_giam_khi_xoa": wd_xoa < wd_goc if orig_hours > 0 else True,
            "luong_thu_tang_khi_nhap": wd_moi > wd_xoa,
            "luong_thu_sau_xoa_moi_bang_sau_xoa_dau": wd_xoa2 == wd_xoa,
        }
        out = {
            "msnv": CODE,
            "ngay": DAY.isoformat(),
            "ky": PERIOD,
            "pay_status": pay.status,
            "buoc": steps,
            "kiem_tra": checks,
            "pass": all(checks.values()),
        }
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        raise SystemExit(0 if out["pass"] else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
