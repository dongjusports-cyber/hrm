"""Seed MSNV 1604 / 1718 / 1519 — nghiệm thu bản vá lương (tái tuyển + benchmark GenusSuite).

Kịch bản (bám test_payroll_resign_rehire + test_payroll_benchmark_1519):
  · 1519 — benchmark kỳ 07/2026, thực lãnh chuẩn 9.682.398
  · 1604 — tái tuyển rồi nghỉ lại; kỳ 08/2026 không còn phiếu lương
  · 1718 — phiếu nháp kỳ 08/2026 bị xóa khi NV nghỉ trước kỳ (31/07/2026)

Chạy:
  docker compose exec api python -m app.scripts.seed_payroll_acceptance_msnv
  docker compose exec api python -m app.scripts.seed_payroll_acceptance_msnv --only 1519
  docker compose exec api python -m app.scripts.seed_payroll_acceptance_msnv --dry-run
  docker compose exec api python -m app.scripts.seed_payroll_acceptance_msnv --no-reset

Sau seed, kiểm nhanh:
  docker compose exec api python -m app.scripts.nghiem_thu_hien_phap --dot 4
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.attendance.models import TimesheetMonth, TimesheetMonthDetail
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets, seed_leave_types
from app.modules.mdm.models import Department, Employee, EmployeeResignation, Team
from app.modules.mdm.schemas import EmployeeCreate, EmployeeRehireRequest, EmployeeResignationCreate
from app.modules.mdm.service import (
    create_employee,
    create_resignation,
    get_or_create_department_by_code,
    rehire_employee,
)
from app.modules.payroll.models import PayComponent, Payslip, PayslipComponent
from app.modules.payroll.period_eligibility import employee_on_payroll_period
from app.modules.payroll.seed_allowances import seed_allowance_types
from app.modules.payroll.service import calculate_period
from app.modules.policy.service import seed_default_package

BENCHMARK_1519_NET = Decimal("9682398")
FIXTURE_CODES = frozenset({"1519", "1604", "1718"})


@dataclass
class SeedReport:
    code: str
    action: str
    detail: str
    ok: bool = True


def _get_team(db: Session, dept_code: str, team_code: str = "T1") -> Team:
    dept = get_or_create_department_by_code(db, dept_code)
    team = (
        db.query(Team)
        .filter(Team.department_id == dept.id, Team.code == team_code)
        .one_or_none()
    )
    if team is None:
        team = Team(department_id=dept.id, code=team_code, name=f"{dept.name} — {team_code}")
        db.add(team)
        db.flush()
    return team


def _purge_employee_payroll_data(db: Session, emp_id: UUID) -> None:
    slip_ids = [r[0] for r in db.query(Payslip.id).filter(Payslip.employee_id == emp_id).all()]
    if slip_ids:
        db.query(PayslipComponent).filter(PayslipComponent.payslip_id.in_(slip_ids)).delete(
            synchronize_session=False
        )
        db.query(Payslip).filter(Payslip.id.in_(slip_ids)).delete(synchronize_session=False)

    ts_ids = [
        r[0]
        for r in db.query(TimesheetMonth.id).filter(TimesheetMonth.employee_id == emp_id).all()
    ]
    if ts_ids:
        db.query(TimesheetMonthDetail).filter(
            TimesheetMonthDetail.timesheet_month_id.in_(ts_ids)
        ).delete(synchronize_session=False)
        db.query(TimesheetMonth).filter(TimesheetMonth.id.in_(ts_ids)).delete(
            synchronize_session=False
        )

    db.query(EmployeeResignation).filter(EmployeeResignation.employee_id == emp_id).delete(
        synchronize_session=False
    )


def _reset_fixture(db: Session, code: str) -> Employee | None:
    emp = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
    if emp is None:
        return None
    _purge_employee_payroll_data(db, emp.id)
    db.delete(emp)
    db.flush()
    return None


def _ensure_prerequisites(db: Session) -> None:
    seed_default_package(db)
    seed_leave_types(db)
    seed_allowance_types(db)
    for code, name, cat in (
        ("SW1", "May 1", "direct"),
        ("B01", "Văn phòng", "admin_indirect"),
    ):
        if db.query(Department).filter(Department.code == code).first() is None:
            db.add(Department(code=code, name=name, category=cat, mitapro_names=[name]))
    db.commit()
    _get_team(db, "SW1")
    _get_team(db, "B01")


def _create_base_employee(
    db: Session,
    *,
    code: str,
    full_name: str,
    dept_code: str,
    contract_salary: Decimal,
    join_date: date,
    contract_signed_at: date | None = None,
    pay_channel: str = "ATM",
    probation_salary: Decimal | None = None,
) -> Employee:
    team = _get_team(db, dept_code)
    out = create_employee(
        db,
        EmployeeCreate.model_validate(
            {
                "employee_code": code,
                "full_name": full_name,
                "team_id": str(team.id),
                "contract_salary": str(contract_salary),
                "probation_salary": str(probation_salary or contract_salary),
                "pay_channel": pay_channel,
                "join_date": join_date.isoformat(),
                "contract_signed_at": (contract_signed_at or join_date).isoformat(),
                "si_enrolled": True,
                "status": "active",
            }
        ),
    )
    return db.query(Employee).filter(Employee.id == out.id).one()


def _set_timesheet_july_1519(db: Session, emp: Employee) -> None:
    """26 công + 1 ngày ALE — không có attendance_days → rebuild giữ nguyên."""
    pay = ensure_pay_period(db, "2026-07")
    rebuild_timesheets(db, "2026-07", recalc_days=False)
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("26")
    ts.al_days = Decimal("1")
    ts.ot_hours_weekday = Decimal("0")
    ts.ot_hours_weekend = Decimal("0")
    ts.ot_hours_holiday = Decimal("0")

    db.query(TimesheetMonthDetail).filter(TimesheetMonthDetail.timesheet_month_id == ts.id).delete(
        synchronize_session=False
    )
    db.add(
        TimesheetMonthDetail(
            timesheet_month_id=ts.id,
            category="ABS_ALE",
            segment="official",
            days=Decimal("1"),
        )
    )
    db.commit()


def seed_1519(db: Session, *, reset: bool, dry_run: bool) -> list[SeedReport]:
    code = "1519"
    reports: list[SeedReport] = []

    if dry_run:
        reports.append(SeedReport(code, "dry-run", "B01/T1 · lương 8.335.000 · công 26+1 ALE · kỳ 07/2026"))
        return reports

    if reset:
        _reset_fixture(db, code)

    emp = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
    if emp is None:
        emp = _create_base_employee(
            db,
            code=code,
            full_name="Nguyễn Benchmark 1519",
            dept_code="B01",
            contract_salary=Decimal("8335000"),
            join_date=date(2015, 3, 15),
            contract_signed_at=date(2015, 6, 15),
        )
        reports.append(SeedReport(code, "created", "NV mới B01/T1"))
    else:
        emp.contract_salary = Decimal("8335000")
        emp.probation_salary = Decimal("8335000")
        emp.join_date = date(2015, 3, 15)
        emp.contract_signed_at = date(2015, 6, 15)
        emp.status = "active"
        emp.resign_date = None
        emp.si_enrolled = True
        emp.team_id = _get_team(db, "B01").id
        db.commit()
        reports.append(SeedReport(code, "updated", "Đồng bộ hồ sơ benchmark"))

    _set_timesheet_july_1519(db, emp)
    calc = calculate_period(db, "2026-07")
    row = next((p for p in calc.payslips if p.employee_code == code), None)
    if row is None:
        reports.append(SeedReport(code, "calculate", "Không có phiếu kỳ 07/2026", ok=False))
        return reports

    net = Decimal(str(row.net))
    ok = net == BENCHMARK_1519_NET
    reports.append(
        SeedReport(
            code,
            "verify",
            f"07/2026 thực lãnh = {net:,.0f} (chuẩn {BENCHMARK_1519_NET:,.0f})".replace(",", "."),
            ok=ok,
        )
    )
    return reports


def seed_1604(db: Session, *, reset: bool, dry_run: bool) -> list[SeedReport]:
    """Tái tuyển fresh_start → nghỉ lại; kỳ 08/2026 loại khỏi bảng lương."""
    code = "1604"
    reports: list[SeedReport] = []

    if dry_run:
        reports.append(
            SeedReport(
                code,
                "dry-run",
                "Nghỉ 20/06 → tái tuyển 01/07 → nghỉ 15/07 → không có phiếu 08/2026",
            )
        )
        return reports

    if reset:
        _reset_fixture(db, code)

    emp = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
    if emp is None:
        emp = _create_base_employee(
            db,
            code=code,
            full_name="NV Tái tuyển 1604",
            dept_code="SW1",
            contract_salary=Decimal("6000000"),
            join_date=date(2020, 1, 15),
            pay_channel="CASH",
            probation_salary=Decimal("6000000"),
        )
        reports.append(SeedReport(code, "created", "NV mới SW1/T1"))
    else:
        emp.status = "active"
        emp.resign_date = None
        emp.join_date = date(2020, 1, 15)
        emp.contract_salary = Decimal("6000000")
        emp.team_id = _get_team(db, "SW1").id
        _purge_employee_payroll_data(db, emp.id)
        db.commit()
        reports.append(SeedReport(code, "reset", "Xóa lịch sử nghỉ/phiếu cũ, về active"))

    team = _get_team(db, "SW1")

    for period in ("2026-06", "2026-07"):
        ensure_pay_period(db, period)
        rebuild_timesheets(db, period, recalc_days=False)

    create_resignation(
        db,
        emp.id,
        EmployeeResignationCreate(
            resign_type_code="DPR",
            last_working_date=date(2026, 6, 20),
            finalize=True,
        ),
    )
    reports.append(SeedReport(code, "resign", "Lần 1: nghỉ 20/06/2026"))

    rehire_employee(
        db,
        emp.id,
        EmployeeRehireRequest(
            rehire_date=date(2026, 7, 1),
            rehire_mode="fresh_start",
            team_id=team.id,
            status="active",
            contract_salary=Decimal("6200000"),
        ),
    )
    reports.append(SeedReport(code, "rehire", "Tái tuyển fresh_start 01/07, lương 6.200.000"))

    calculate_period(db, "2026-06")
    calculate_period(db, "2026-07")

    create_resignation(
        db,
        emp.id,
        EmployeeResignationCreate(
            resign_type_code="DPR",
            last_working_date=date(2026, 7, 15),
            finalize=True,
        ),
    )
    reports.append(SeedReport(code, "resign", "Lần 2: nghỉ 15/07/2026"))

    db.refresh(emp)
    pay_jul = ensure_pay_period(db, "2026-07")
    pay_aug = ensure_pay_period(db, "2026-08")
    rebuild_timesheets(db, "2026-08", recalc_days=False)

    in_jul = employee_on_payroll_period(emp, pay_jul.date_from, pay_jul.date_to)
    in_aug = employee_on_payroll_period(emp, pay_aug.date_from, pay_aug.date_to)
    reports.append(
        SeedReport(
            code,
            "eligibility",
            f"07/2026={'có' if in_jul else 'không'} · 08/2026={'có' if in_aug else 'không'}",
            ok=in_jul and not in_aug,
        )
    )

    calc_aug = calculate_period(db, "2026-08")
    has_aug = any(p.employee_code == code for p in calc_aug.payslips)
    stale = (
        db.query(Payslip)
        .join(Employee, Employee.id == Payslip.employee_id)
        .filter(Payslip.pay_period_id == pay_aug.id, Employee.employee_code == code)
        .count()
    )
    reports.append(
        SeedReport(
            code,
            "verify",
            f"08/2026 phiếu API={'có' if has_aug else 'không'} · DB payslip={stale}",
            ok=not has_aug and stale == 0,
        )
    )
    return reports


def seed_1718(db: Session, *, reset: bool, dry_run: bool) -> list[SeedReport]:
    """Tính nháp kỳ 08/2026 trước → nghỉ 31/07 → tính lại, không còn phiếu âm."""
    code = "1718"
    reports: list[SeedReport] = []

    if dry_run:
        reports.append(
            SeedReport(code, "dry-run", "Tính 08/2026 → nghỉ 31/07/2026 → tính lại, không phiếu")
        )
        return reports

    if reset:
        _reset_fixture(db, code)

    emp = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
    if emp is None:
        emp = _create_base_employee(
            db,
            code=code,
            full_name="NV Nghỉ trước kỳ 1718",
            dept_code="SW1",
            contract_salary=Decimal("6000000"),
            join_date=date(2020, 1, 15),
            pay_channel="CASH",
            probation_salary=Decimal("6000000"),
        )
        reports.append(SeedReport(code, "created", "NV mới SW1/T1"))
    else:
        emp.status = "active"
        emp.resign_date = None
        emp.join_date = date(2020, 1, 15)
        emp.contract_salary = Decimal("6000000")
        emp.team_id = _get_team(db, "SW1").id
        _purge_employee_payroll_data(db, emp.id)
        db.commit()
        reports.append(SeedReport(code, "reset", "Về active, xóa phiếu/nghỉ cũ"))

    ensure_pay_period(db, "2026-08")
    rebuild_timesheets(db, "2026-08", recalc_days=False)
    calc1 = calculate_period(db, "2026-08")
    had_slip = any(p.employee_code == code for p in calc1.payslips)
    reports.append(
        SeedReport(code, "precalc", f"Tính 08/2026 lần 1: {'có' if had_slip else 'không'} phiếu")
    )

    create_resignation(
        db,
        emp.id,
        EmployeeResignationCreate(
            resign_type_code="DPR",
            last_working_date=date(2026, 7, 31),
            finalize=True,
        ),
    )
    reports.append(SeedReport(code, "resign", "Nghỉ 31/07/2026 (trước kỳ 08/2026)"))

    db.refresh(emp)
    pay_aug = ensure_pay_period(db, "2026-08")
    eligible = employee_on_payroll_period(emp, pay_aug.date_from, pay_aug.date_to)
    reports.append(
        SeedReport(
            code,
            "eligibility",
            f"08/2026 thuộc kỳ={'có' if eligible else 'không'}",
            ok=not eligible,
        )
    )

    calc2 = calculate_period(db, "2026-08")
    has_slip = any(p.employee_code == code for p in calc2.payslips)
    stale = (
        db.query(Payslip)
        .join(Employee, Employee.id == Payslip.employee_id)
        .filter(Payslip.pay_period_id == pay_aug.id, Employee.employee_code == code)
        .count()
    )
    reports.append(
        SeedReport(
            code,
            "verify",
            f"08/2026 phiếu API={'có' if has_slip else 'không'} · DB payslip={stale}",
            ok=not has_slip and stale == 0,
        )
    )
    return reports


def run(*, only: set[str] | None = None, reset: bool = True, dry_run: bool = False) -> list[SeedReport]:
    targets = FIXTURE_CODES if only is None else FIXTURE_CODES & only
    if not targets:
        raise SystemExit("Không có MSNV hợp lệ — dùng --only 1519 hoặc 1604,1718")

    db = SessionLocal()
    all_reports: list[SeedReport] = []
    try:
        if not dry_run:
            _ensure_prerequisites(db)

        runners = {
            "1519": seed_1519,
            "1604": seed_1604,
            "1718": seed_1718,
        }
        for code in sorted(targets):
            all_reports.extend(runners[code](db, reset=reset, dry_run=dry_run))

        if not dry_run:
            db.commit()
    finally:
        db.close()
    return all_reports


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed MSNV 1604/1718/1519 cho nghiệm thu bản vá lương",
    )
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Chỉ seed các MSNV (vd. 1519 hoặc 1604,1718)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Không xóa NV fixture cũ trước khi seed lại",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in kịch bản, không ghi DB")
    args = parser.parse_args()

    only_set: set[str] | None = None
    if args.only.strip():
        only_set = {c.strip() for c in args.only.split(",") if c.strip()}

    reports = run(only=only_set, reset=not args.no_reset, dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "DONE"
    ok_count = sum(1 for r in reports if r.ok)
    print(f"{mode}: {ok_count}/{len(reports)} bước OK")
    for r in reports:
        mark = "OK" if r.ok else "FAIL"
        print(f"  [{mark}] {r.code} · {r.action}: {r.detail}")


if __name__ == "__main__":
    main()
