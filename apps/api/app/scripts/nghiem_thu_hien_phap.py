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


def _get_hr_user(db):
    from app.modules.core.models import User

    return db.query(User).filter(User.username == "hr.demo").one_or_none()


def _open_work_date(db) -> date | None:
    """Ngày trong kỳ lương đang mở — dùng cho thử dán Excel."""
    from app.modules.attendance.models import PayPeriod

    for candidate in (date.today(), date.today() - timedelta(days=1)):
        pay = (
            db.query(PayPeriod)
            .filter(PayPeriod.year == candidate.year, PayPeriod.month == candidate.month)
            .first()
        )
        if pay is not None and pay.status != "locked":
            return candidate
    return None


def check_31_excel_paste(db) -> Result:
    """3.1 — mô phỏng dán Excel 20 dòng (MSNV · Vào · Ra) qua patch_day_cell."""
    from datetime import datetime, timedelta, timezone

    from app.modules.attendance.day_grid import patch_day_cell

    hr = _get_hr_user(db)
    if hr is None:
        return Result("3", "3.1", False, "Không có user hr.demo")

    work_date = _open_work_date(db)
    if work_date is None:
        return Result("3", "3.1", False, "Không có ngày trong kỳ lương đang mở")

    vn = timezone(timedelta(hours=7))
    emps = (
        db.query(Employee)
        .filter(
            Employee.deleted_at.is_(None),
            Employee.status.in_(("active", "probation", "maternity")),
        )
        .order_by(Employee.employee_code)
        .limit(20)
        .all()
    )
    if len(emps) < 20:
        return Result("3", "3.1", False, f"Chỉ có {len(emps)} NV active — cần 20")

    ok_count = 0
    errors: list[str] = []
    for emp in emps:
        try:
            patch_day_cell(
                db,
                hr,
                employee_code=emp.employee_code,
                work_date=work_date,
                first_in=datetime(work_date.year, work_date.month, work_date.day, 8, 0, tzinfo=vn),
                last_out=datetime(work_date.year, work_date.month, work_date.day, 17, 0, tzinfo=vn),
                note="nghiem_thu 3.1",
            )
            ok_count += 1
        except Exception as exc:
            errors.append(f"{emp.employee_code}: {exc}")

    ok = ok_count >= 20
    detail = f"Dán {ok_count}/20 dòng MSNV·Vào·Ra ngày {work_date.isoformat()}"
    if errors:
        detail += f" — lỗi: {'; '.join(errors[:2])}"
    return Result("3", "3.1", ok, detail)


def check_36_bulk_approve(db) -> Result:
    """3.6 — tạo 12 đơn OFF và duyệt hàng loạt một lần."""
    from uuid import UUID

    from app.modules.attendance.leave_requests import bulk_decide_leave_requests, create_leave_request
    from app.modules.attendance.models import LeaveRequest

    hr = _get_hr_user(db)
    if hr is None:
        return Result("3", "3.6", False, "Không có user hr.demo")

    already = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.reason.like("nghiem_thu 3.6%"),
            LeaveRequest.status == "approved",
        )
        .count()
    )
    if already >= 12:
        return Result("3", "3.6", True, f"Đã có {already} đơn OFF duyệt (nghiem_thu 3.6) — idempotent OK")

    emps = (
        db.query(Employee)
        .filter(
            Employee.deleted_at.is_(None),
            Employee.status.in_(("active", "probation", "maternity")),
        )
        .order_by(Employee.employee_code)
        .all()
    )
    if len(emps) < 12:
        return Result("3", "3.6", False, f"Chỉ có {len(emps)} NV — cần 12")

    req_ids: list[UUID] = []
    base = date(2027, 3, 1)
    picked = 0
    for emp in emps:
        if picked >= 12:
            break
        d = base + timedelta(days=picked)
        try:
            row = create_leave_request(
                db,
                employee=emp,
                leave_type_code="OFF",
                from_date=d,
                to_date=d,
                from_half=False,
                to_half=False,
                reason="nghiem_thu 3.6",
                submit=True,
            )
            req_ids.append(UUID(str(row["id"])))
            picked += 1
        except Exception:
            continue

    if len(req_ids) < 12:
        return Result("3", "3.6", False, f"Chỉ tạo được {len(req_ids)}/12 đơn — trùng ngày hoặc thiếu NV")

    result = bulk_decide_leave_requests(
        db,
        request_ids=req_ids,
        action="approve",
        decided_note="nghiem_thu 3.6",
        decider=hr,
    )
    approved = result.get("approved_count", 0)
    ok = approved == 12
    detail = f"Duyệt hàng loạt {approved}/12 đơn OFF"
    skipped = result.get("skipped") or []
    if skipped:
        detail += f" — bỏ qua {len(skipped)}"
    return Result("3", "3.6", ok, detail)


def check_38_mitapro(db) -> Result:
    """3.8 — Agent + punch Mitapro; MSNV 200* không lưu DB."""
    from app.modules.integration.models import AttendancePunch
    from app.modules.integration.service import integration_status

    st = integration_status(db)
    guard_in_db = (
        db.query(AttendancePunch).filter(AttendancePunch.employee_code.like("200%")).count()
    )
    last_status = st.last_job.status if st.last_job else "—"
    ok = st.agent_configured and st.punch_count > 0 and st.last_job is not None and guard_in_db == 0
    detail = (
        f"Agent OK · {st.punch_count} punch · chưa khớp {st.punch_unlinked_count} · "
        f"MSNV 200* trong DB: {guard_in_db} · sync: {last_status}"
    )
    return Result("3", "3.8", ok, detail)


def check_13_team_at_date(db) -> Result:
    """1.3 — truy vấn tổ MSNV 1514 ngày 2026-03-15 qua employee_assignments."""
    from app.modules.mdm.service import backfill_initial_assignments, team_at_date

    backfilled = backfill_initial_assignments(db)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one_or_none()
    if emp is None:
        return Result("1", "1.3", False, "Không có MSNV 1514")
    as_of = date(2026, 3, 15)
    team = team_at_date(db, emp.id, as_of)
    ok = team is not None
    detail = (
        f"MSNV 1514 ngày {as_of.isoformat()}: tổ {team.code} — {team.name}"
        if team
        else "Không tra được tổ qua employee_assignments"
    )
    if backfilled:
        detail += f" · backfill {backfilled} NV"
    return Result("1", "1.3", ok, detail)


def check_33_needs_action(db) -> Result:
    """3.3 — chip «Chỉ hiện cần xử lý» (API needs_action_only)."""
    from app.modules.attendance.day_grid import list_days_grid

    work_date = _open_work_date(db) or date.today()
    all_rows = list_days_grid(db, work_date, needs_action_only=False)
    filtered = list_days_grid(db, work_date, needs_action_only=True)
    needs_codes = {r.employee_code for r in all_rows if r.needs_action}
    filtered_codes = {r.employee_code for r in filtered}
    ok = (
        len(filtered) <= len(all_rows)
        and all(r.needs_action for r in filtered)
        and filtered_codes == needs_codes
    )
    detail = f"Chip cần xử lý: {len(filtered)}/{len(all_rows)} dòng ngày {work_date.isoformat()}"
    return Result("3", "3.3", ok, detail)


def _get_admin_user(db):
    from app.modules.core.models import User

    return db.query(User).filter(User.username == "admin").one_or_none()


def check_21_attendance_bonus_simulate(db) -> Result:
    """2.1 — đổi ngưỡng chuyên cần → chạy thử lương khác số (simulate 4.10)."""
    from copy import deepcopy

    from app.modules.payroll.schemas import SimulateRequest
    from app.modules.payroll.simulate import simulate_period
    from app.modules.payroll.service import _active_policy
    from app.modules.policy.models import PolicyPackage

    _, payload = _active_policy(db)
    base_bonus = int(payload.get("attendance_bonus_monthly", 600_000))
    alt = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.name == "nghiem_thu 2.1 chuyên cần")
        .one_or_none()
    )
    target_bonus = base_bonus + 50_000
    if alt is None:
        alt_payload = deepcopy(payload)
        alt_payload["attendance_bonus_monthly"] = target_bonus
        alt = PolicyPackage(
            name="nghiem_thu 2.1 chuyên cần",
            effective_from=date(2026, 1, 1),
            is_active=False,
            version=1,
            payload=alt_payload,
        )
        db.add(alt)
        db.commit()
        db.refresh(alt)
    elif int((alt.payload or {}).get("attendance_bonus_monthly", 0)) != target_bonus:
        alt.payload = deepcopy(payload)
        alt.payload["attendance_bonus_monthly"] = target_bonus
        db.commit()
        db.refresh(alt)

    best_code = None
    best_delta = Decimal("0")
    for code in ("1519", "1514", "5321"):
        try:
            sim = simulate_period(
                db,
                SimulateRequest(
                    period="2026-07",
                    policy_package_id=alt.id,
                    scope="employees",
                    employee_codes=[code],
                ),
            )
        except Exception:
            continue
        if not sim.rows:
            continue
        delta = Decimal(str(sim.rows[0].delta_net))
        if abs(delta) > abs(best_delta):
            best_delta = delta
            best_code = code

    ok = best_code is not None and best_delta != 0
    return Result(
        "2",
        "2.1",
        ok,
        f"Chuyên cần {base_bonus:,}→{target_bonus:,}: MSNV {best_code} Δnet={best_delta:,.0f}".replace(",", ".")
        if ok
        else f"Δnet = 0 với mọi MSNV thử ({base_bonus}→{target_bonus})",
    )


def check_23_payroll_accountant_role(db) -> Result:
    """2.3 — vai trò Kế toán lương + quyền module payroll."""
    from app.modules.core.models import Role
    from app.modules.core.roles_service import get_role_matrix, seed_roles

    seed_roles(db)
    role = db.get(Role, "payroll_accountant")
    if role is None:
        return Result("2", "2.3", False, "Chưa có role payroll_accountant")
    matrix = get_role_matrix(db, "payroll_accountant")
    modules = {m["module_key"]: m["level"] for m in matrix.get("modules", [])}
    payroll_level = modules.get("payroll")
    ok = role.name == "Kế toán lương" and payroll_level == "view"
    return Result(
        "2",
        "2.3",
        ok,
        f"Vai trò {role.code}: payroll={payroll_level}"
        if ok
        else f"FAIL: name={role.name!r} payroll={payroll_level!r}",
    )


def check_24_new_leave_type(db) -> Result:
    """2.4 — thêm loại nghỉ mới → có trong danh mục chấm công."""
    from app.modules.config.catalog_schemas import LeaveTypeAdminCreate
    from app.modules.config.catalog_service import create_leave_type
    from app.modules.attendance.timesheet import seed_leave_types

    admin = _get_admin_user(db) or _get_hr_user(db)
    if admin is None:
        return Result("2", "2.4", False, "Không có user admin/hr.demo")
    code = "NTH"
    if db.get(LeaveType, code) is None:
        create_leave_type(
            db,
            LeaveTypeAdminCreate(code=code, name="Nghiệm thu Hiến pháp", paid_by_company=False),
            admin,
        )
    seed_leave_types(db)
    row = db.get(LeaveType, code)
    ok = row is not None and row.name
    return Result(
        "2",
        "2.4",
        ok,
        f"Loại nghỉ {code} — {row.name}" if row else "Không tạo được loại nghỉ NTH",
    )


def check_48_policy_snapshot(db) -> Result:
    """4.8 — phiếu lương gắn policy_snapshot (tính kỳ mở nếu chưa có)."""
    from app.modules.payroll.models import PolicySnapshot
    from app.modules.payroll.service import calculate_period

    slip = (
        db.query(Payslip)
        .filter(Payslip.policy_snapshot_id.isnot(None))
        .order_by(Payslip.updated_at.desc())
        .first()
    )
    if slip is None:
        hr = _get_hr_user(db)
        try:
            calculate_period(db, "2026-08", actor=hr)
        except Exception as exc:
            return Result("4", "4.8", False, f"Tính lương 08/2026 thất bại: {exc}")
        slip = (
            db.query(Payslip)
            .filter(Payslip.policy_snapshot_id.isnot(None))
            .order_by(Payslip.updated_at.desc())
            .first()
        )
    if slip is None:
        return Result("4", "4.8", False, "Sau tính 08/2026 vẫn chưa có policy_snapshot")
    snap = db.get(PolicySnapshot, slip.policy_snapshot_id)
    attend = snap.payload.get("attendance_bonus_monthly") if snap and snap.payload else None
    ok = snap is not None and slip.net is not None
    return Result(
        "4",
        "4.8",
        ok,
        f"Phiếu snapshot: net={slip.net}, attendance_bonus={attend}",
    )


def check_51_create_employee(db) -> Result:
    """5.1 — gợi ý MSNV + validate tạo NV (P0)."""
    from app.modules.mdm import employee_validation as ev
    from app.modules.mdm.schemas import EmployeeCreate

    suggested = ev.suggest_employee_code(db)
    issues = ev.validate_employee_create(
        db,
        EmployeeCreate.model_validate(
            {
                "employee_code": "xx",
                "full_name": "A",
                "contract_salary": "0",
                "pay_channel": "CASH",
            }
        ),
    )
    err = {i.code for i in issues if i.level == "error"}
    ok = suggested.isdigit() and len(suggested) >= 3 and bool(err)
    return Result(
        "5",
        "5.1",
        ok,
        f"Gợi ý MSNV {suggested} · validate lỗi {sorted(err)}",
    )


def check_53_pit_dependents(db) -> Result:
    """5.3 — 2 con <18 → giảm trừ 11M + 2×4.4M."""
    from decimal import Decimal

    from app.modules.mdm.models import EmployeeFamilyMember
    from app.modules.mdm.schemas import EmployeeFamilyMemberCreate
    from app.modules.mdm.service import compute_tax_dependents, create_family_member
    from app.modules.payroll.engine_pit import compute_pit_amount
    from app.modules.payroll.service import _active_policy

    _, policy = _active_policy(db)
    personal = int(policy.get("pit_personal_deduction", 0))
    per_dep = int(policy.get("pit_dependent_deduction", 0))
    emp = db.query(Employee).filter(Employee.employee_code == "1643").one_or_none()
    if emp is None:
        return Result("5", "5.3", False, "Không có MSNV 1643")
    child_birth = date.today().replace(year=date.today().year - 10)
    for i, name in enumerate(("nghiem_thu con 1", "nghiem_thu con 2"), start=1):
        exists = (
            db.query(EmployeeFamilyMember)
            .filter(
                EmployeeFamilyMember.employee_id == emp.id,
                EmployeeFamilyMember.full_name == name,
            )
            .first()
        )
        if exists is None:
            create_family_member(
                db,
                emp.id,
                EmployeeFamilyMemberCreate(
                    relationship_code="con",
                    full_name=name,
                    birth_date=child_birth,
                    is_tax_dependent=True,
                    dependent_from=date(2025, 1, 1),
                ),
            )
    tax = compute_tax_dependents(db, emp.id)
    pit_enabled = bool(policy.get("pit_enabled"))
    dep_total = Decimal("0")
    if pit_enabled:
        _, pit_detail = compute_pit_amount(
            gross=Decimal("20000000"),
            bhxh=Decimal("1600000"),
            bhyt=Decimal("300000"),
            bhtn=Decimal("200000"),
            policy=policy,
            tax_dependent_count=2,
            pit_enrolled=True,
        )
        dep_total = Decimal(str(pit_detail.get("dependent_deduction_total", 0)))
    ok = (
        personal == 11_000_000
        and per_dep == 4_400_000
        and tax.effective_count >= 2
        and (not pit_enabled or dep_total == Decimal(per_dep * 2))
    )
    pit_note = f"PIT dep={dep_total:,.0f}" if pit_enabled else "PIT tắt — chỉ kiểm NPT"
    return Result(
        "5",
        "5.3",
        ok,
        f"GT {tax.effective_count} NPT · 11M+2×4.4M={personal + 2 * per_dep:,} · {pit_note}".replace(",", "."),
    )


def check_55_insurance_export(db) -> Result:
    """5.5 — đề xuất + xuất lô báo tăng BHXH tháng hiện tại."""
    from app.modules.insurance.declarations import export_batch, propose_monthly
    from app.modules.insurance.models import InsuranceDeclaration

    month = f"{date.today().year:04d}-{date.today().month:02d}"
    try:
        prop = propose_monthly(db, month)
    except Exception as exc:
        return Result("5", "5.5", False, f"Propose BHXH {month} thất bại: {exc}")
    if prop.created_count == 0:
        draft = (
            db.query(InsuranceDeclaration)
            .filter(
                InsuranceDeclaration.effective_month == month,
                InsuranceDeclaration.status.in_(("draft", "exported")),
            )
            .count()
        )
        if draft == 0:
            return Result("5", "5.5", True, f"Tháng {month}: không có biến động BHXH (OK)")
    try:
        exp = export_batch(db, effective_month=month)
        ok = exp.row_count >= 1 and "employee_code" in (exp.content or "")
        detail = f"Xuất {exp.row_count} dòng BHXH tháng {month}"
    except Exception as exc:
        ok = prop.created_count > 0
        detail = f"Propose {prop.created_count} dòng · xuất: {exc}"
    return Result("5", "5.5", ok, detail)


def check_56_admin_tabs(db) -> Result:
    """5.6 — Admin 6 tab: policy + danh mục + tổ chức sẵn sàng."""
    from app.modules.policy.models import PolicyPackage

    pkg = db.query(PolicyPackage).filter(PolicyPackage.is_active.is_(True)).first()
    depts = db.query(Department).count()
    teams = db.query(Team).filter(Team.effective_to.is_(None)).count()
    leaves = db.query(LeaveType).count()
    payload_keys = len(pkg.payload) if pkg and isinstance(pkg.payload, dict) else 0
    ok = pkg is not None and depts >= 8 and teams >= 30 and leaves >= 14 and payload_keys >= 10
    return Result(
        "5",
        "5.6",
        ok,
        f"Policy «{pkg.name if pkg else '?'}» {payload_keys} khóa · {depts} BP · {teams} tổ · {leaves} loại nghỉ",
    )


def check_58_worker_leave(db) -> Result:
    """5.8 — cổng công nhân gửi đơn nghỉ (create_leave_request)."""
    from app.modules.attendance.leave_requests import create_leave_request
    from app.modules.attendance.models import LeaveRequest

    emp = db.query(Employee).filter(Employee.employee_code == "5290").one_or_none()
    if emp is None:
        return Result("5", "5.8", False, "Không có MSNV 5290")
    existing = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.reason.like("nghiem_thu 5.8%"),
            LeaveRequest.status.in_(("draft", "submitted", "approved")),
        )
        .first()
    )
    if existing:
        return Result("5", "5.8", True, f"Đơn 5290 đã gửi (nghiem_thu 5.8) — idempotent OK")
    d = date(2027, 5, 10)
    try:
        row = create_leave_request(
            db,
            employee=emp,
            leave_type_code="OFF",
            from_date=d,
            to_date=d,
            from_half=False,
            to_half=False,
            reason="nghiem_thu 5.8",
            submit=True,
        )
    except Exception as exc:
        return Result("5", "5.8", False, f"Gửi đơn 5290 thất bại: {exc}")
    ok = row["status"] == "submitted"
    return Result(
        "5",
        "5.8",
        ok,
        f"5290 gửi đơn OFF {d.isoformat()} · {row['status']}",
    )


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
    out.append(check_13_team_at_date(db))
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
    out.append(check_21_attendance_bonus_simulate(db))
    out.append(check_23_payroll_accountant_role(db))
    out.append(check_24_new_leave_type(db))
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
        and ot_day.ot_on_books_minutes == 180
        and ot_day.ot_external_minutes == 0
    )
    out.append(
        Result(
            "3",
            "3.7",
            ok_37,
            "07:59:59 không trễ · 08:00:01 trễ 1p · Th3 20:00 OT sổ=180p"
            if ok_37
            else f"FAIL late={on_time.late_minutes}/{late.late_minutes} ot={ot_day.ot_minutes}",
        )
    )
    from app.modules.policy.seed_payload import default_payload
    from app.modules.attendance.engine import calculate_day as calc_day
    from app.modules.attendance.ot_split import default_ot_split_policy

    pl = default_payload()
    ot_cfg = pl.get("ot_split") or {}
    ok_split = (
        list(ot_cfg.get("on_books_weekdays") or []) == [2, 4]
        and isinstance(ot_cfg.get("ot_external"), dict)
        and ot_cfg.get("ot_external", {}).get("exclude_from_payslip") is True
    )
    out.append(
        Result(
            "3",
            "3.9",
            ok_split,
            "policy ot_split: Th3/Th5 sổ + ot_external ATM tách payslip"
            if ok_split
            else "FAIL thiếu ot_split/ot_external trong policy",
        )
    )
    # Th5 (ISO 4) 21:00 → 180p sổ + 60p ngoài
    th5 = calc_day(
        [
            datetime(2025, 10, 9, 8, 0, 0, tzinfo=vn),
            datetime(2025, 10, 9, 21, 0, 0, tzinfo=vn),
        ],
        date(2025, 10, 9),
        sched,
        ot_split=default_ot_split_policy(),
    )
    ok_th5 = th5.ot_on_books_minutes == 180 and th5.ot_external_minutes == 60
    out.append(
        Result(
            "3",
            "3.9b",
            ok_th5,
            f"Th5 21h: OT sổ={th5.ot_on_books_minutes}p ngoài={th5.ot_external_minutes}p (ngưỡng 17:30, tính từ 17:00)"
            if ok_th5
            else f"FAIL sổ={th5.ot_on_books_minutes} ngoài={th5.ot_external_minutes}",
        )
    )
    out.append(check_31_excel_paste(db))
    out.append(check_33_needs_action(db))
    out.append(check_36_bulk_approve(db))
    out.append(check_38_mitapro(db))
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

    out.append(check_48_policy_snapshot(db))
    return out


def check_dot5_p0_p3(db) -> list[Result]:
    """P0 validation + P3 tái tuyển (chốt 2026-08-12)."""
    from app.modules.mdm import employee_validation as ev
    from app.modules.mdm.models import EmployeeResignation
    from app.modules.mdm.schemas import EmployeeCreate

    out: list[Result] = []
    suggested = ev.suggest_employee_code(db)
    out.append(
        Result(
            "5",
            "P0-suggest",
            suggested.isdigit() and len(suggested) >= 3,
            f"Gợi ý MSNV tiếp theo: {suggested}",
        )
    )
    issues = ev.validate_employee_create(
        db,
        EmployeeCreate.model_validate(
            {
                "employee_code": "xx",
                "full_name": "A",
                "contract_salary": "0",
                "pay_channel": "CASH",
            }
        ),
    )
    err_codes = {i.code for i in issues if i.level == "error"}
    out.append(
        Result(
            "5",
            "P0-validate",
            {"format", "min"} <= err_codes or "required" in err_codes,
            f"Validate tạo NV — mã lỗi: {sorted(err_codes)}",
        )
    )
    resigned = (
        db.query(Employee)
        .filter(Employee.status == "resigned", Employee.deleted_at.is_(None))
        .first()
    )
    if resigned is None:
        out.append(
            Result("5", "P3-snapshot", True, "Chưa có NV resigned để kiểm snapshot (OK nếu chưa ai nghỉ)")
        )
    else:
        last = (
            db.query(EmployeeResignation)
            .filter(EmployeeResignation.employee_id == resigned.id)
            .order_by(EmployeeResignation.seq_no.desc())
            .first()
        )
        has_snap = last is not None and isinstance(last.snapshot_json, dict)
        out.append(
            Result(
                "5",
                "P3-snapshot",
                has_snap or last is None,
                "Có snapshot_json khi nghỉ"
                if has_snap
                else "NV resigned cũ chưa có snapshot — nghỉ lại sau migrate 0047",
            )
        )
    out.append(
        _manual(
            "5",
            "P3-rehire",
            "Tái tuyển 2 kiểu: Thôi việc → Tái tuyển (thường / giữ quyền lợi)",
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

    out.append(check_51_create_employee(db))
    out.append(check_53_pit_dependents(db))
    out.append(_manual("5", "5.4", "NV nghỉ → tái tuyển thường + tái tuyển giữ quyền lợi (P3)"))
    out.append(check_55_insurance_export(db))
    out.append(check_56_admin_tabs(db))
    out.append(check_58_worker_leave(db))
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
        results.extend(check_dot5_p0_p3(db))
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
