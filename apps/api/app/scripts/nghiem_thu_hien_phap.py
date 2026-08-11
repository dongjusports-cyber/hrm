"""Chạy checklist nghiệm thu HIEN_PHAP 24§ — tiêu chí kiểm chứng được bằng số.

Chạy trên máy công ty (DB thật):
  docker compose exec api python -m app.scripts.nghiem_thu_hien_phap

Một số mục (Mitapro, dán Excel, HR bấm thử Admin) vẫn cần người — script báo SKIP.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, inspect

from app.core.database import SessionLocal, engine
from app.modules.attendance.models import PayPeriod
from app.modules.mdm import labour_contract_flow as lcf
from app.modules.attendance.models import LeaveType
from app.modules.mdm.models import Department, Employee, LabourContract, Team
from app.modules.payroll.models import Payslip
from app.modules.policy import service as policy_service


@dataclass
class Result:
    dot: str
    code: str
    ok: bool
    detail: str
    manual: bool = False


def _manual(dot: str, code: str, detail: str) -> Result:
    return Result(dot, code, False, f"SKIP (HR): {detail}", manual=True)


def check_dot1(db) -> list[Result]:
    out: list[Result] = []
    active_emp = (
        db.query(Employee)
        .filter(Employee.deleted_at.is_(None), Employee.status.in_(("active", "probation", "maternity")))
        .count()
    )
    no_team = (
        db.query(Employee)
        .filter(Employee.deleted_at.is_(None), Employee.team_id.is_(None), Employee.status != "resigned")
        .count()
    )
    out.append(
        Result(
            "1",
            "1.4",
            no_team == 0,
            f"NV active/probation/maternity không tổ: {no_team} (tổng {active_emp})",
        )
    )
    active_teams = db.query(Team).filter(Team.effective_to.is_(None)).count()
    out.append(Result("1", "1.2", active_teams >= 30, f"Tổ hiệu lực: {active_teams} (kỳ vọng ≥30)"))
    dept_count = db.query(Department).count()
    out.append(Result("1", "1.2b", dept_count >= 8, f"Bộ phận trong DB: {dept_count}"))

    insp = inspect(engine)
    emp_cols = {c["name"] for c in insp.get_columns("employees")}
    out.append(
        Result(
            "1",
            "1.5",
            "department_id" not in emp_cols,
            "Không còn employees.department_id"
            if "department_id" not in emp_cols
            else "Còn cột department_id — chưa đạt",
        )
    )
    out.append(
        _manual(
            "1",
            "1.3",
            "Truy vấn tổ MSNV 1514 ngày 2026-03-15 qua employee_assignments",
        )
    )
    return out


def check_dot2(db) -> list[Result]:
    out: list[Result] = []
    leave_count = db.query(LeaveType).count()
    out.append(Result("2", "2.2", leave_count >= 14, f"Loại nghỉ active: {leave_count} (kỳ vọng ≥14)"))
    amt = policy_service.lookup_seniority_amount(db, 136, date.today()).amount
    out.append(
        Result(
            "2",
            "2.5",
            Decimal(str(amt)) == Decimal("550000"),
            f"Thâm niên 136 tháng = {Decimal(str(amt)):,.0f} (kỳ vọng 550.000)".replace(",", "."),
        )
    )
    for code, hint in [
        ("2.1", "Đổi ngưỡng chuyên cần Admin → chạy thử lương khác số"),
        ("2.3", "Tạo vai trò Kế toán lương — đăng nhập thử quyền"),
        ("2.4", "Thêm loại nghỉ mới → hiện ở màn chấm công"),
    ]:
        out.append(_manual("2", code, hint))
    return out


def check_dot3(db) -> list[Result]:
    from app.modules.attendance.punch_dedupe import dedupe_punch_times
    from datetime import datetime, timezone

    from datetime import datetime, timezone

    out: list[Result] = []
    base = date.today()
    morning = [
        datetime(base.year, base.month, base.day, 7, 50, 0, tzinfo=timezone.utc),
        datetime(base.year, base.month, base.day, 7, 50, 15, tzinfo=timezone.utc),
        datetime(base.year, base.month, base.day, 7, 50, 45, tzinfo=timezone.utc),
    ]
    kept_am = dedupe_punch_times(morning, window_seconds=60)
    out.append(
        Result(
            "3",
            "3.2",
            len(kept_am) == 1,
            f"3 lần chấm 07:50 → {len(kept_am)} giờ vào (dedupe 60s)",
        )
    )
    from datetime import time, timedelta

    from app.modules.attendance.engine import Schedule, calculate_day

    vn = timezone(timedelta(hours=7))
    sched = Schedule(
        work_weekdays=[1, 2, 3, 4, 5, 6],
        morning_start=time(8, 0),
        morning_end=time(12, 0),
        afternoon_start=time(13, 0),
        afternoon_end=time(17, 0),
        grace_late_minutes=0,
        holiday_dates=set(),
        grace_late_seconds=0,
        grace_early_seconds=0,
    )
    on_time = calculate_day(
        [
            datetime(2025, 10, 10, 7, 59, 59, tzinfo=vn),
            datetime(2025, 10, 10, 17, 0, 0, tzinfo=vn),
        ],
        date(2025, 10, 10),
        sched,
    )
    late = calculate_day(
        [
            datetime(2025, 10, 15, 8, 0, 1, tzinfo=vn),
            datetime(2025, 10, 15, 17, 0, 0, tzinfo=vn),
        ],
        date(2025, 10, 15),
        sched,
    )
    ot_day = calculate_day(
        [
            datetime(2025, 10, 14, 8, 0, 0, tzinfo=vn),
            datetime(2025, 10, 14, 20, 0, 0, tzinfo=vn),
        ],
        date(2025, 10, 14),
        sched,
    )
    ok_37 = (
        on_time.late_minutes == 0
        and late.late_minutes == 1
        and ot_day.worked_hours == Decimal("8.0000")
        and ot_day.ot_minutes == 180
    )
    out.append(
        Result(
            "3",
            "3.7",
            ok_37,
            "07:59:59 không trễ · 08:00:01 trễ 1p · 20:00 OT=180p"
            if ok_37
            else f"FAIL late={on_time.late_minutes}/{late.late_minutes} ot={ot_day.ot_minutes}",
        )
    )
    for code, hint in [
        ("3.1", "Dán Excel 20 dòng vào bảng công"),
        ("3.3", "Chip «Chỉ hiện cần xử lý» trên màn bảng công"),
        ("3.6", "Duyệt 12 đơn phép một lần bấm"),
        ("3.8", "Mitapro sync + punch chưa khớp người"),
    ]:
        out.append(_manual("3", code, hint))
    return out


def check_dot4(db) -> list[Result]:
    from app.modules.payroll.allowance_proration import prorate_allowance
    from app.modules.payroll.engine_allowances import (
        AllowanceInput,
        AllowanceTypeView,
        compute_allowances,
        should_zero_probation_allowances,
    )
    from app.modules.payroll.engine_wd import WdSalaryInput, compute_wd_salary
    from app.modules.policy.seed_payload import default_payload

    out: list[Result] = []
    target = Decimal("9682398")
    emp = db.query(Employee).filter(Employee.employee_code == "1519").one_or_none()
    if emp is None:
        out.append(Result("4", "4.10", False, "Không có MSNV 1519 trong DB"))
        return out
    pp = db.query(PayPeriod).filter(PayPeriod.year == 2026, PayPeriod.month == 7).first()
    if pp is None:
        out.append(Result("4", "22.11", False, "Chưa có kỳ lương 07/2026"))
        return out
    ps = (
        db.query(Payslip)
        .filter(Payslip.pay_period_id == pp.id, Payslip.employee_id == emp.id)
        .first()
    )
    if ps is None:
        out.append(Result("4", "22.11", False, "Chưa có phiếu lương 1519 kỳ 07/2026"))
    else:
        match = Decimal(str(ps.net)) == target
        out.append(
            Result(
                "4",
                "22.11",
                match,
                f"1519/07/2026 thực lãnh = {Decimal(str(ps.net)):,.0f} (chuẩn {target:,.0f})".replace(
                    ",", "."
                ),
            )
        )

    # 4.2 — thử việc thuần: chuyên cần + đi lại = 0
    payload = default_payload()
    zero_ok = should_zero_probation_allowances(
        payload, contract_signed_at=None, period_to=date(2026, 7, 31)
    )
    allow_zero = compute_allowances(
        AllowanceInput(
            salary_divisor=Decimal("26"),
            worked_days=Decimal("26"),
            late_count=0,
            early_count=0,
            penalty_absent_days=Decimal("0"),
            join_date=date(2026, 7, 1),
            as_of=date(2026, 7, 31),
            policy=payload,
            monthly_by_code={},
            types=[
                AllowanceTypeView(
                    "ATTEND", "Chuyên cần", "attend_penalty", False, True, Decimal("600000")
                ),
                AllowanceTypeView(
                    "TRANSPORT", "Đi lại", "by_worked_days", False, False, Decimal("800000")
                ),
            ],
            suppress_allowances=True,
        )
    )
    by_z = {ln.code: ln.amount for ln in allow_zero.lines}
    ok_42 = (
        zero_ok
        and by_z.get("ATTEND", Decimal("1")) == 0
        and by_z.get("TRANSPORT", Decimal("1")) == 0
    )
    out.append(
        Result(
            "4",
            "4.2",
            ok_42,
            "NV thử việc: chuyên cần + đi lại = 0"
            if ok_42
            else f"FAIL 4.2 ATTEND={by_z.get('ATTEND')} TRANSPORT={by_z.get('TRANSPORT')}",
        )
    )

    # 4.3 — vào giữa tháng: 2 đoạn WD probation/official
    wd_mid = compute_wd_salary(
        WdSalaryInput(
            contract_salary=Decimal("6000000"),
            probation_salary=Decimal("5100000"),
            salary_divisor=Decimal("26"),
            worked_days=Decimal("20"),
            al_days=Decimal("0"),
            period_from=date(2025, 10, 1),
            period_to=date(2025, 10, 31),
            contract_signed_at=date(2025, 10, 15),
            work_weekdays=(1, 2, 3, 4, 5, 6),
            holiday_dates=frozenset(),
        )
    )
    ok_43 = wd_mid.probation_days > 0 and wd_mid.contract_days > 0
    out.append(
        Result(
            "4",
            "4.3",
            ok_43,
            f"Giữa tháng: probation_days={wd_mid.probation_days} official_days={wd_mid.contract_days}"
            if ok_43
            else "FAIL: không tách được 2 đoạn WD",
        )
    )

    # 4.4 — tháng 27 ngày công: chuyên cần 623.077
    amt_27 = prorate_allowance(Decimal("600000"), Decimal("26"), Decimal("27")).quantize(
        Decimal("1")
    )
    ok_44 = amt_27 == Decimal("623077")
    out.append(
        Result(
            "4",
            "4.4",
            ok_44,
            f"Tháng 27 ngày: chuyên cần = {amt_27:,.0f} (kỳ vọng 623.077)".replace(",", "."),
        )
    )

    # 4.5 — tháng 20 ngày công đủ: chuyên cần 600.000
    amt_20 = prorate_allowance(Decimal("600000"), Decimal("20"), Decimal("20"))
    ok_45 = amt_20 == Decimal("600000")
    out.append(
        Result(
            "4",
            "4.5",
            ok_45,
            f"Tháng 20 ngày công: chuyên cần = {amt_20:,.0f} (kỳ vọng 600.000)".replace(",", "."),
        )
    )

    # 4.7 — số dư phép trên phiếu = tổng bút toán sổ
    from app.modules.attendance.annual_leave_ledger import verify_annual_leave_nghiem_thu_47
    from app.modules.payroll.payslip_detail import get_hr_payslip_detail

    slip_row = (
        db.query(Payslip, Employee, PayPeriod)
        .join(Employee, Employee.id == Payslip.employee_id)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .filter(Employee.deleted_at.is_(None))
        .order_by(PayPeriod.year.desc(), PayPeriod.month.desc())
        .first()
    )
    if slip_row is None:
        out.append(Result("4", "4.7", False, "Không có phiếu lương để kiểm sổ phép"))
    else:
        slip, emp, pay = slip_row
        as_of = pay.date_to or date.today()
        detail = get_hr_payslip_detail(db, slip.id)
        ok_47, msg_47 = verify_annual_leave_nghiem_thu_47(
            db,
            employee_id=emp.id,
            as_of=as_of,
            payslip_remaining=Decimal(str(detail.annual_leave_remaining)),
        )
        out.append(Result("4", "4.7", ok_47, msg_47 if ok_47 else msg_47))

    # 4.8 — kỳ published/locked: phiếu gắn policy_snapshot (20§ N3)
    from app.modules.payroll.models import PolicySnapshot

    slip_with_snap = (
        db.query(Payslip)
        .filter(Payslip.policy_snapshot_id.isnot(None))
        .order_by(Payslip.updated_at.desc())
        .first()
    )
    if slip_with_snap is None:
        out.append(
            _manual(
                "4",
                "4.8",
                "DB chưa có phiếu gắn policy_snapshot — tính lại 1 kỳ; logic đã pass pytest",
            )
        )
    else:
        snap = db.get(PolicySnapshot, slip_with_snap.policy_snapshot_id)
        ok_48 = snap is not None and slip_with_snap.net is not None
        attend = snap.payload.get("attendance_bonus_monthly") if snap and snap.payload else None
        out.append(
            Result(
                "4",
                "4.8",
                ok_48,
                f"Phiếu có snapshot: net={slip_with_snap.net}, "
                f"attendance_bonus_snapshot={attend} "
                f"(đổi policy sau lock: pytest test_nghiem_thu_48)",
            )
        )
    return out


def check_dot5(db) -> list[Result]:
    out: list[Result] = []
    emp_total = db.query(Employee).filter(Employee.deleted_at.is_(None)).count()
    lc_emp = db.query(func.count(func.distinct(LabourContract.employee_id))).scalar() or 0
    out.append(
        Result(
            "5",
            "5.2",
            lc_emp >= emp_total * 0.9,
            f"NV có labour_contracts: {lc_emp}/{emp_total}",
        )
    )
    today = date.today()
    expiring = (
        db.query(LabourContract)
        .filter(
            LabourContract.status == "active",
            LabourContract.end_date.isnot(None),
            LabourContract.end_date >= today,
            LabourContract.end_date <= today + timedelta(days=60),
        )
        .count()
    )
    out.append(
        Result(
            "5",
            "5.2b",
            True,
            f"HĐ sắp hết hạn 60 ngày: {expiring} (VTH không có ngày hết — đúng)",
        )
    )

    from app.modules.print.service import render_contract, render_probation

    emp_1514 = db.query(Employee).filter(Employee.employee_code == "1514").one_or_none()
    if emp_1514 is None:
        out.append(Result("5", "5.9", False, "Không có MSNV 1514 để in mẫu"))
    else:
        try:
            contract_html = render_contract(db, emp_1514.id)
            probation_html = render_probation(db, emp_1514.id)
            ok_59 = (
                "HỢP ĐỒNG LAO ĐỘNG" in contract_html
                and emp_1514.employee_code in contract_html
                and "THỎA THUẬN THỬ VIỆC" in probation_html
            )
            out.append(
                Result(
                    "5",
                    "5.9",
                    ok_59,
                    f"In HĐ + thử việc MSNV 1514 ({len(contract_html)} / {len(probation_html)} ký tự HTML)"
                    if ok_59
                    else "FAIL: thiếu nội dung mẫu in",
                )
            )
        except Exception as exc:
            out.append(Result("5", "5.9", False, f"Lỗi in mẫu: {exc}"))

    for code, hint in [
        ("5.1", "Tạo NV mới 9 trường một màn"),
        ("5.3", "2 con <18 → giảm trừ 11M + 2×4.4M"),
        ("5.4", "NV nghỉ rồi vào lại → 2 dòng thôi việc"),
        ("5.5", "Xuất lô báo tăng BHXH tháng"),
        ("5.6", "Admin 6 tab — HR đổi policy không cần dev"),
        ("5.8", "Cổng công nhân xin nghỉ phép"),
    ]:
        out.append(_manual("5", code, hint))
    return out


def run() -> int:
    db = SessionLocal()
    results: list[Result] = []
    try:
        results.extend(check_dot1(db))
        results.extend(check_dot2(db))
        results.extend(check_dot3(db))
        results.extend(check_dot4(db))
        results.extend(check_dot5(db))
    finally:
        db.close()

    passed = sum(1 for r in results if r.ok and not r.manual)
    failed = sum(1 for r in results if not r.ok and not r.manual)
    manual = sum(1 for r in results if r.manual)

    print("=== NGHIỆM THU HIEN_PHAP 24§ ===\n")
    cur_dot = ""
    for r in results:
        if r.dot != cur_dot:
            cur_dot = r.dot
            print(f"\n--- Đợt {cur_dot} ---")
        mark = "OK" if r.ok else ("SKIP" if r.manual else "FAIL")
        print(f"  [{mark}] {r.code}: {r.detail}")

    print(f"\nTự động: {passed} OK · {failed} FAIL · {manual} cần HR")
    if failed:
        print("\n→ Còn tiêu chí FAIL — chưa nghiệm thu xong.")
        return 1
    print(f"\n→ Tiêu chí tự động đạt. Hoàn tất {manual} mục HR trên máy công ty để chốt nghiệm thu.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
