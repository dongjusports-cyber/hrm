"""Nạp lại hồ sơ NV từ «Dữ liệu công nhân» JSON (export_employee_snapshots.py).

Chạy:
  python -m app.scripts.import_employee_snapshots HIEN_PHAP/Dữ liệu công nhân
  python -m app.scripts.import_employee_snapshots HIEN_PHAP/Dữ liệu công nhân --dry-run
  python -m app.scripts.import_employee_snapshots ... --with-attendance

(Vẫn chấp nhận đường dẫn cũ HIEN_PHAP/_SNAPSHOTS/nhan-vien.)
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.attendance.models import AttendanceDay, WorkShift  # noqa: F401
from app.modules.core.models import User  # noqa: F401
from app.modules.mdm.models import Department, Employee, LabourContract, Team
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent
from app.modules.payroll.seed_allowances import normalize_legacy_allowance_amount
from app.scripts.employee_data_paths import resolve_hien_phap
from app.scripts.import_employee_list_1108 import (
    ORG_EFFECTIVE,
    _apply_profile,
    _dept_by_name,
    _find_team,
    _norm,
    _upsert_labour_contract,
    ensure_team,
    load_valid_teams,
)
from app.scripts import import_genussuite_2026 as gs

PROFILE_FIELDS = {
    "full_name",
    "gender",
    "birth_date",
    "birth_place_code",
    "nationality_code",
    "ethnicity_code",
    "religion_code",
    "marital_status",
    "children_count",
    "education_code",
    "id_number",
    "id_issue_date",
    "id_issue_place_code",
    "permanent_address",
    "temporary_address",
    "urgent_contact",
    "si_book_no",
    "bank_account",
    "pay_channel",
    "position_code",
    "job_code",
    "position_title",
    "join_date",
    "contract_signed_at",
    "probation_salary",
    "contract_salary",
    "si_base_override",
    "si_enrolled",
    "pit_enrolled",
    "tax_dependent_count",
    "union_fee_override",
    "status",
    "resign_date",
    "phone",
    "photo_path",
}


def _parse_value(key: str, val: Any) -> Any:
    if val is None:
        return None
    if key.endswith("_id") and key != "employee_code" and isinstance(val, str):
        try:
            return UUID(val)
        except ValueError:
            return val
    if isinstance(val, str):
        if key.endswith("_date") or key in ("join_date", "resign_date", "contract_signed_at"):
            try:
                return date.fromisoformat(val[:10])
            except ValueError:
                return val
        if key.endswith("_at"):
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                return val
        if key in (
            "contract_salary",
            "probation_salary",
            "si_base_override",
            "union_fee_override",
            "worked_hours",
        ) or "salary" in key or "amount" in key or key.endswith("_hours"):
            try:
                return Decimal(val)
            except Exception:
                return val
        if key in ("children_count", "tax_dependent_count", "punch_count", "late_minutes", "early_minutes"):
            try:
                return int(val)
            except ValueError:
                return val
        if key in ("si_enrolled", "pit_enrolled", "is_workday", "is_locked"):
            return val in (True, "true", "True", "1", 1)
    return val


def _prof_from_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    prof = dict(snap.get("sources", {}).get("empinfo_profile") or {})
    assign = snap.get("sources", {}).get("empinfo_assignment") or {}
    db_prof = snap.get("profile") or {}
    for k, v in db_prof.items():
        if k in ("id", "team_id", "created_at", "updated_at", "deleted_at"):
            continue
        if v is not None and v != "" and k not in prof:
            prof[k] = _parse_value(k, v)
    if assign:
        prof.setdefault("department_name", assign.get("department_name"))
        prof.setdefault("team_name", assign.get("team_name"))
    return prof


def _resolve_team(db: Session, snap: dict[str, Any], valid_teams: set[str]) -> Team | None:
    org = snap.get("organization") or {}
    prof = _prof_from_snapshot(snap)
    dept_name = org.get("department_name") or prof.get("department_name")
    team_name = org.get("team_name") or prof.get("team_name")
    if not dept_name or not team_name:
        return None
    dept = _dept_by_name(db, dept_name)
    if dept is None:
        return None
    return ensure_team(db, dept, team_name, valid_teams=valid_teams)


def _apply_allowances(db: Session, emp: Employee, items: list[dict[str, Any]]) -> None:
    db.query(EmployeeAllowanceAssignment).filter(
        EmployeeAllowanceAssignment.employee_id == emp.id
    ).delete(synchronize_session=False)
    for item in items:
        code = item.get("component_code")
        if not code:
            continue
        comp = db.query(PayComponent).filter(PayComponent.code == code).first()
        if comp is None:
            continue
        raw_amount = _parse_value("amount", item.get("amount"))
        amount = normalize_legacy_allowance_amount(code, raw_amount)
        db.add(
            EmployeeAllowanceAssignment(
                employee_id=emp.id,
                allowance_type_id=comp.id,
                amount=amount,
                meta=item.get("meta"),
            )
        )


def _apply_attendance(db: Session, emp: Employee, days: list[dict[str, Any]]) -> int:
    n = 0
    for raw in days:
        work_date = _parse_value("work_date", raw.get("work_date"))
        if not isinstance(work_date, date):
            continue
        row = (
            db.query(AttendanceDay)
            .filter(AttendanceDay.employee_id == emp.id, AttendanceDay.work_date == work_date)
            .one_or_none()
        )
        if row is None:
            row = AttendanceDay(employee_id=emp.id, work_date=work_date)
            db.add(row)
        for key, val in raw.items():
            if key in ("id", "employee_id", "work_date", "updated_at"):
                continue
            if hasattr(AttendanceDay, key):
                setattr(row, key, _parse_value(key, val))
        n += 1
    return n


def import_one(
    db: Session,
    snap: dict[str, Any],
    *,
    valid_teams: set[str],
    with_attendance: bool,
    dry_run: bool,
) -> str:
    code = snap["employee_code"]
    prof = _prof_from_snapshot(snap)
    assign = snap.get("sources", {}).get("empinfo_assignment") or {}

    if dry_run:
        return f"{code}: dry-run OK"

    team = _resolve_team(db, snap, valid_teams)
    emp = db.query(Employee).filter(Employee.employee_code == code).first()
    if emp is None:
        emp = Employee(employee_code=code, status="active")
        db.add(emp)
    emp.deleted_at = None
    if team:
        emp.team_id = team.id

    _apply_profile(emp, assign, prof)
    _upsert_labour_contract(db, emp, prof)
    _apply_allowances(db, emp, snap.get("allowances") or [])

    att_n = 0
    if with_attendance and snap.get("attendance_days"):
        att_n = _apply_attendance(db, emp, snap["attendance_days"])

    return f"{code}: OK | phu cap {len(snap.get('allowances') or [])} | cong {att_n}"


def run(
    snapshot_dir: Path,
    *,
    with_attendance: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
) -> None:
    employees_dir = snapshot_dir / "employees"
    if not employees_dir.is_dir():
        raise FileNotFoundError(f"Không thấy {employees_dir}")

    files = sorted(employees_dir.glob("*.json"))
    if limit:
        files = files[:limit]

    hien_phap = resolve_hien_phap(snapshot_dir)
    empinfo = None
    for child in hien_phap.iterdir():
        if child.is_dir() and "nh" in child.name.lower():
            empinfo = child
            break
    valid_teams: set[str] = set()
    if empinfo:
        xlsx = empinfo / "Bộ phận_11.08.xlsx"
        if xlsx.is_file():
            valid_teams = load_valid_teams(xlsx)

    db = SessionLocal()
    try:
        ok = 0
        for path in files:
            snap = json.loads(path.read_text(encoding="utf-8"))
            msg = import_one(
                db,
                snap,
                valid_teams=valid_teams,
                with_attendance=with_attendance,
                dry_run=dry_run,
            )
            print(msg)
            ok += 1
        if not dry_run:
            db.commit()
        print(f"Hoan tat: {ok}/{len(files)} NV")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp lại Dữ liệu công nhân (JSON từng nhân viên)")
    parser.add_argument(
        "snapshot_dir",
        type=Path,
        help="Thư mục chứa employees/*.json (vd. HIEN_PHAP/Dữ liệu công nhân)",
    )
    parser.add_argument("--with-attendance", action="store_true", help="Ghi cả attendance_days")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(
        args.snapshot_dir.resolve(),
        with_attendance=args.with_attendance,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
