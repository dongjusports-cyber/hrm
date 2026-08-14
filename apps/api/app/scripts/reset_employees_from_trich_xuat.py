"""Xóa sạch dữ liệu nhân viên test và nạp lại từ trich_xuat GenusSuite.

Nguồn: HIEN_PHAP/Thông tin danh sách nhân viên/trich_xuat_140826/employees.json
       + photos/{MSNV}.jpg

Chạy (host — DB localhost:5432):
  cd apps/api
  set DATABASE_URL=postgresql+psycopg://djhrm:djhrm_local_change_me@localhost:5432/djhrm
  python -m app.scripts.reset_employees_from_trich_xuat

  python -m app.scripts.reset_employees_from_trich_xuat --dry-run
  python -m app.scripts.reset_employees_from_trich_xuat --no-wipe
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.attendance.models import WorkShift  # noqa: F401
from app.modules.audit.models import AuditLog
from app.modules.core.models import User  # noqa: F401
from app.modules.mdm.models import Employee
from app.modules.mdm.service import _photo_dir
from app.scripts.import_employee_list_1108 import (
    _dept_by_name,
    _upsert_labour_contract,
    ensure_team,
    load_valid_teams,
)

WIPE_EMPLOYEE_SQL = [
    "DELETE FROM disputes",
    "DELETE FROM payslip_components",
    "DELETE FROM payslips",
    "DELETE FROM payslip_adjustments",
    "DELETE FROM timesheet_month_details",
    "DELETE FROM timesheet_adjustments",
    "DELETE FROM timesheet_months",
    "DELETE FROM leave_requests",
    "DELETE FROM annual_leave_entries",
    "DELETE FROM annual_leave_ledger",
    "DELETE FROM attendance_days",
    "DELETE FROM employee_bonuses",
    "DELETE FROM insurance_declarations",
    "DELETE FROM employee_resignations",
    "DELETE FROM employee_family_members",
    "DELETE FROM employee_educations",
    "DELETE FROM employee_experiences",
    "DELETE FROM employee_health_checks",
    "DELETE FROM employee_salary_history",
    "DELETE FROM employee_assignments",
    "DELETE FROM labour_contracts",
    "DELETE FROM employee_allowance_assignments",
    "DELETE FROM employee_violations",
    "DELETE FROM employee_documents",
    "UPDATE attendance_punches SET employee_id = NULL",
    "DELETE FROM users WHERE role = 'worker'",
    "UPDATE employees SET team_id = NULL, position_code = NULL, job_code = NULL",
    "DELETE FROM employees",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_trich_xuat_dir() -> Path:
    base = repo_root() / "HIEN_PHAP"
    for child in base.iterdir():
        if child.is_dir() and "nh" in child.name.lower() and "vi" in child.name.lower():
            for sub in sorted(child.glob("trich_xuat_*"), reverse=True):
                if (sub / "employees.json").is_file():
                    return sub
    raise FileNotFoundError("Không tìm thấy trich_xuat_*/employees.json")


def _coerce(key: str, val: Any) -> Any:
    if val is None or val == "":
        return None
    if key.endswith("_date") or key in (
        "join_date",
        "resign_date",
        "contract_signed_at",
        "contract_start",
        "contract_end",
        "left_date",
    ):
        if isinstance(val, date):
            return val
        return date.fromisoformat(str(val)[:10])
    if key in ("contract_salary", "probation_salary", "si_base_override", "union_fee_override"):
        return Decimal(str(val))
    if key in ("children_count", "tax_dependent_count"):
        return int(val)
    if key in ("si_enrolled", "pit_enrolled"):
        return val in (True, "true", "True", 1, "1")
    return val


PROFILE_FIELDS = (
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
    "position_title",
    "join_date",
    "contract_signed_at",
    "probation_salary",
    "contract_salary",
    "si_enrolled",
    "pit_enrolled",
    "tax_dependent_count",
    "status",
    "resign_date",
    "phone",
)


def _contract_prof(profile: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("contract_start", "contract_end", "left_date"):
        v = profile.get(key)
        out[key] = _coerce(key, v) if v else None
    out["contract_type_code"] = profile.get("contract_type_code")
    sal = profile.get("contract_salary")
    out["contract_salary"] = Decimal(str(sal)) if sal not in (None, "") else None
    return out


def _sync_employment_tab(emp: Employee, profile: dict[str, Any]) -> None:
    """Gán đúng tab: VTH/HD* → chính thức; TV → thử việc (03§ effective_status)."""
    ctype = profile.get("contract_type_code")
    signed = _coerce("contract_signed_at", profile.get("contract_signed_at"))
    start = _coerce("contract_start", profile.get("contract_start"))
    if signed:
        emp.contract_signed_at = signed
    elif start:
        emp.contract_signed_at = start
    if profile.get("left_date"):
        emp.status = "resigned"
        emp.resign_date = _coerce("resign_date", profile["left_date"])
        return
    if ctype == "TV":
        emp.status = "probation"
    elif ctype in ("VTH", "HD1", "HD2"):
        emp.status = "active"
    elif start:
        emp.status = "active"


def _apply_trich_profile(emp: Employee, profile: dict[str, Any]) -> None:
    for key in PROFILE_FIELDS:
        if key not in profile:
            continue
        val = _coerce(key, profile.get(key))
        if val is not None and val != "":
            setattr(emp, key, val)
    if not emp.pay_channel:
        emp.pay_channel = "ATM"
    _sync_employment_tab(emp, profile)


def _copy_photo(trich_dir: Path, emp: Employee, profile: dict[str, Any]) -> bool:
    rel = profile.get("photo_file")
    if not rel:
        return False
    src = trich_dir / str(rel).replace("\\", "/")
    if not src.is_file() or src.stat().st_size < 500:
        return False
    dest = _photo_dir() / f"{emp.id}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    emp.photo_path = dest.name
    return True


def wipe_employees(db: Session, *, dry_run: bool) -> None:
    print("== Xoa sach du lieu nhan vien (giu cay to chuc + user HR) ==")
    if dry_run:
        print(f"  (dry-run) se xoa ~{db.query(Employee).count()} employees")
        return
    for stmt in WIPE_EMPLOYEE_SQL:
        db.execute(text(stmt))
    db.flush()
    print(f"  Da xoa — con {db.query(Employee).count()} employees")


def _is_valid_row(profile: dict[str, Any]) -> bool:
    name = (profile.get("full_name") or "").strip()
    if not name:
        return False
    dept = (profile.get("department_name") or "").lower()
    if dept.startswith("total") or "grand total" in dept:
        return False
    return True


def import_trich_xuat(
    db: Session,
    trich_dir: Path,
    *,
    valid_teams: set[str],
) -> tuple[int, int, int, int]:
    data = json.loads((trich_dir / "employees.json").read_text(encoding="utf-8"))
    rows = data.get("employees") or []
    created = updated = photos = 0

    skipped = 0
    for row in rows:
        code = str(row.get("employee_code") or "").strip()
        profile = row.get("profile") or {}
        if not code or not _is_valid_row(profile):
            skipped += 1
            continue

        dept_name = profile.get("department_name")
        team_name = profile.get("team_name")
        team = None
        if dept_name and team_name:
            dept = _dept_by_name(db, dept_name)
            if dept:
                team = ensure_team(db, dept, team_name, valid_teams=valid_teams)

        emp = db.query(Employee).filter(Employee.employee_code == code).first()
        if emp is None:
            emp = Employee(
                employee_code=code,
                full_name=profile["full_name"].strip(),
                status="active",
            )
            db.add(emp)
            created += 1
        else:
            updated += 1
        emp.deleted_at = None
        if team:
            emp.team_id = team.id

        _apply_trich_profile(emp, profile)
        db.flush()
        _upsert_labour_contract(db, emp, _contract_prof(profile))
        if _copy_photo(trich_dir, emp, profile):
            photos += 1

    return created, updated, photos, skipped


def _load_valid_teams() -> set[str]:
    for xlsx in (repo_root() / "HIEN_PHAP").rglob("*.xlsx"):
        name = xlsx.name.lower()
        if "bộ phận" in name or "bo phan" in name or name.startswith("b"):
            try:
                teams = load_valid_teams(xlsx)
                if teams:
                    return teams
            except Exception:
                continue
    return set()


def run(trich_dir: Path, *, wipe: bool = True, dry_run: bool = False) -> None:
    valid_teams = _load_valid_teams()

    print(f"Nguon: {trich_dir / 'employees.json'}")
    print(f"To hop le: {len(valid_teams)}")

    db = SessionLocal()
    try:
        if wipe:
            wipe_employees(db, dry_run=dry_run)
        if dry_run:
            print("(dry-run) khong ghi DB")
            return

        created, updated, photos, skipped = import_trich_xuat(db, trich_dir, valid_teams=valid_teams)
        db.add(
            AuditLog(
                actor_username="system.reset_employees_from_trich_xuat",
                action="reset_import_trich_xuat",
                entity_type="employee",
                entity_id="bulk",
                summary=(
                    f"Xoa sach NV test + nap trich_xuat: "
                    f"moi {created}, cap nhat {updated}, anh {photos}, bo qua {skipped} dong loi."
                ),
            )
        )
        db.commit()
        total = db.query(Employee).filter(Employee.deleted_at.is_(None)).count()
        print(f"HOAN TAT: {total} NV | anh {photos} | bo qua {skipped}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, default=None)
    parser.add_argument("--no-wipe", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    trich_dir = (args.dir or default_trich_xuat_dir()).resolve()
    if not (trich_dir / "employees.json").is_file():
        raise SystemExit(f"Khong thay employees.json trong {trich_dir}")

    run(trich_dir, wipe=not args.no_wipe, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
