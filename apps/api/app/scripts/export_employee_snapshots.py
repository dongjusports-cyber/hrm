"""Trích xuất 1 file JSON / nhân viên — gom HIEN_PHAP + DB để nạp lại sau khi test.

Thư mục mặc định: HIEN_PHAP/Dữ liệu công nhân/ (trước đây: _SNAPSHOTS/nhan-vien).

Nguồn:
  - HIEN_PHAP/Thông tin danh sách nhân viên/ (3 file Excel)
  - HIEN_PHAP/Salary/2.Salary table for *.2026.xls
  - HIEN_PHAP/Công/ (quét file — nếu có)
  - PostgreSQL hiện tại (hồ sơ, HĐ, phụ cấp, ngày công…)

Chạy (từ apps/api):
  python -m app.scripts.export_employee_snapshots
  python -m app.scripts.export_employee_snapshots --out C:/DATA/HRM/dj-hrm/dj-hrm/HIEN_PHAP/Dữ liệu công nhân
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.attendance.models import AttendanceDay, TimesheetMonth
from app.modules.mdm.models import Department, Employee, EmployeeFamilyMember, LabourContract, Team
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent
from app.modules.payroll.seed_allowances import normalize_legacy_allowance_amount
from app.scripts import import_genussuite_2026 as gs
from app.scripts.employee_data_paths import default_employee_data_dir, import_command
from app.scripts.import_employee_list_1108 import load_assignments, load_profiles

SCHEMA_VERSION = 1
SALARY_MONTH_TAGS = {
    "Jan": "2026-01",
    "Feb": "2026-02",
    "Mar": "2026-03",
    "Apr": "2026-04",
    "May": "2026-05",
    "June": "2026-06",
    "July": "2026-07",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def find_empinfo_dir(hien_phap: Path) -> Path | None:
    for child in hien_phap.iterdir():
        if child.is_dir() and "nh" in child.name.lower() and "vi" in child.name.lower():
            return child
    return None


def find_cong_dir(hien_phap: Path) -> Path | None:
    for child in hien_phap.iterdir():
        if not child.is_dir():
            continue
        name = unicodedata.normalize("NFC", child.name).lower()
        if name in ("công", "cong") or name.endswith("công"):
            return child
    return None


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Không serialize được: {type(value)!r}")


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default)


def _row_dict(row: Any, *, skip: frozenset[str] = frozenset()) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in row.__table__.columns:
        if col.name in skip:
            continue
        out[col.name] = getattr(row, col.name)
    return out


def _salary_month_key(path: Path) -> str | None:
    name = path.name
    for tag, key in SALARY_MONTH_TAGS.items():
        if tag in name:
            return key
    return None


def load_salary_sources(salary_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """{msnv: {2026-07: {...}, ...}}"""
    merged: dict[str, dict[str, dict[str, Any]]] = {}
    for path in sorted(salary_dir.glob("2.Salary table for *.2026.xls")):
        period = _salary_month_key(path)
        if not period:
            continue
        for msnv, rec in gs.parse_month(str(path)).items():
            merged.setdefault(msnv, {})[period] = dict(rec)
    return merged


def load_empinfo_sources(empinfo: Path) -> tuple[dict[str, dict], dict[str, dict], list[str]]:
    profiles: dict[str, dict] = {}
    assignments: dict[str, dict] = {}
    warnings: list[str] = []

    profile_path = empinfo / "Thông tin danh sách công nhân 11.08.26.xls"
    assign_path = empinfo / "Danh sách Nhân Viên - Bộ phận hiện tại.xls"

    if profile_path.is_file():
        for code, row in load_profiles(profile_path).items():
            profiles[code] = {k: v for k, v in row.items()}
    else:
        warnings.append(f"Thiếu file hồ sơ: {profile_path.name}")

    if assign_path.is_file():
        for code, row in load_assignments(assign_path).items():
            assignments[code] = {k: v for k, v in row.items()}
    else:
        warnings.append(f"Thiếu file bộ phận/tổ: {assign_path.name}")

    return profiles, assignments, warnings


def scan_cong_files(cong_dir: Path | None) -> list[str]:
    if cong_dir is None or not cong_dir.is_dir():
        return []
    return sorted(str(p.relative_to(cong_dir)) for p in cong_dir.rglob("*") if p.is_file())


def _org_block(emp: Employee) -> dict[str, Any]:
    team = emp.team
    dept = team.department if team else None
    return {
        "department_code": dept.code if dept else None,
        "department_name": dept.name if dept else None,
        "team_code": team.code if team else None,
        "team_name": team.name if team else None,
    }


def _allowances(db: Session, emp_id: UUID) -> list[dict[str, Any]]:
    rows = (
        db.query(EmployeeAllowanceAssignment, PayComponent.code)
        .join(PayComponent, PayComponent.id == EmployeeAllowanceAssignment.allowance_type_id)
        .filter(EmployeeAllowanceAssignment.employee_id == emp_id)
        .all()
    )
    out: list[dict[str, Any]] = []
    for assign, code in rows:
        amount = normalize_legacy_allowance_amount(code, assign.amount)
        out.append(
            {
                "component_code": code,
                "amount": amount,
                "meta": assign.meta,
            }
        )
    return out


def _attendance_days(db: Session, emp_id: UUID, *, year: int | None) -> list[dict[str, Any]]:
    q = db.query(AttendanceDay).filter(AttendanceDay.employee_id == emp_id)
    if year is not None:
        q = q.filter(
            AttendanceDay.work_date >= date(year, 1, 1),
            AttendanceDay.work_date <= date(year, 12, 31),
        )
    return [_row_dict(d) for d in q.order_by(AttendanceDay.work_date).all()]


def _timesheets(db: Session, emp_id: UUID) -> list[dict[str, Any]]:
    rows = db.query(TimesheetMonth).filter(TimesheetMonth.employee_id == emp_id).all()
    return [_row_dict(r) for r in rows]


def build_snapshot(
    db: Session,
    code: str,
    *,
    profiles: dict[str, dict],
    assignments: dict[str, dict],
    salary: dict[str, dict[str, Any]],
    cong_files: list[str],
    attendance_year: int | None,
) -> dict[str, Any]:
    emp = (
        db.query(Employee)
        .filter(Employee.employee_code == code, Employee.deleted_at.is_(None))
        .one_or_none()
    )

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "employee_code": code,
        "organization": {},
        "profile": None,
        "labour_contracts": [],
        "allowances": [],
        "family_members": [],
        "attendance_days": [],
        "timesheet_months": [],
        "sources": {
            "empinfo_profile": profiles.get(code),
            "empinfo_assignment": assignments.get(code),
            "salary_by_month": salary.get(code, {}),
            "cong_files_index": cong_files,
        },
    }

    if emp is not None:
        snapshot["organization"] = _org_block(emp)
        snapshot["profile"] = _row_dict(emp)
        snapshot["labour_contracts"] = [
            _row_dict(c) for c in db.query(LabourContract).filter(LabourContract.employee_id == emp.id).all()
        ]
        snapshot["allowances"] = _allowances(db, emp.id)
        snapshot["family_members"] = [
            _row_dict(m) for m in db.query(EmployeeFamilyMember).filter(EmployeeFamilyMember.employee_id == emp.id).all()
        ]
        if attendance_year is not None:
            snapshot["attendance_days"] = _attendance_days(db, emp.id, year=attendance_year)
        snapshot["timesheet_months"] = _timesheets(db, emp.id)
    else:
        prof = profiles.get(code) or {}
        assign = assignments.get(code) or {}
        snapshot["organization"] = {
            "department_code": None,
            "department_name": prof.get("department_name") or assign.get("department_name"),
            "team_code": None,
            "team_name": prof.get("team_name") or assign.get("team_name"),
        }
        snapshot["profile"] = {
            "employee_code": code,
            "full_name": prof.get("full_name") or assign.get("full_name"),
            "status": prof.get("status", "active"),
            **{k: v for k, v in prof.items() if k not in ("department_name", "team_name")},
        }

    return snapshot


def run(
    *,
    hien_phap: Path,
    out_dir: Path,
    attendance_year: int | None = 2026,
    dry_run: bool = False,
) -> None:
    empinfo = find_empinfo_dir(hien_phap)
    salary_dir = hien_phap / "Salary"
    cong_dir = find_cong_dir(hien_phap)

    if empinfo is None:
        raise FileNotFoundError(f"Không tìm thấy thư mục danh sách NV trong {hien_phap}")
    if not salary_dir.is_dir():
        raise FileNotFoundError(f"Không tìm thấy {salary_dir}")

    profiles, assignments, warnings = load_empinfo_sources(empinfo)
    salary = load_salary_sources(salary_dir)
    cong_files = scan_cong_files(cong_dir)

    codes: set[str] = set(profiles) | set(assignments) | set(salary)
    db = SessionLocal()
    try:
        db_codes = [
            r[0]
            for r in db.query(Employee.employee_code)
            .filter(Employee.deleted_at.is_(None))
            .all()
        ]
        codes |= set(db_codes)
    finally:
        db.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    employees_dir = out_dir / "employees"
    employees_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    db = SessionLocal()
    try:
        for code in sorted(codes, key=lambda c: (len(c), c)):
            snap = build_snapshot(
                db,
                code,
                profiles=profiles,
                assignments=assignments,
                salary=salary,
                cong_files=cong_files,
                attendance_year=attendance_year,
            )
            if dry_run:
                continue
            safe = re.sub(r"[^\w.-]", "_", code)
            (employees_dir / f"{safe}.json").write_text(_dump(snap) + "\n", encoding="utf-8")
            written += 1
    finally:
        db.close()

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "employee_count": len(codes),
        "files_written": written,
        "sources": {
            "empinfo_dir": str(empinfo),
            "salary_dir": str(salary_dir),
            "cong_dir": str(cong_dir) if cong_dir else None,
            "cong_file_count": len(cong_files),
            "salary_employees": len(salary),
            "profile_employees": len(profiles),
            "assignment_employees": len(assignments),
        },
        "warnings": warnings,
        "reload_command": import_command(hien_phap),
    }
    if not dry_run:
        (out_dir / "manifest.json").write_text(_dump(manifest) + "\n", encoding="utf-8")

    print(f"MSNV: {len(codes)} | da ghi: {written} file -> {employees_dir}")
    if warnings:
        for w in warnings:
            print(f"  ! {w}")
    if cong_files:
        print(f"  Cong: {len(cong_files)} file (chi muc)")
    else:
        print(f"  Công: thu muc trong — ngay cong lay tu DB (neu co)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trích xuất Dữ liệu công nhân (JSON từng nhân viên)")
    parser.add_argument(
        "--hien-phap",
        type=Path,
        default=repo_root() / "HIEN_PHAP",
        help="Thư mục HIEN_PHAP",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Thư mục output (manifest + employees/) — mặc định: HIEN_PHAP/Dữ liệu công nhân",
    )
    parser.add_argument(
        "--attendance-year",
        type=int,
        default=2026,
        help="Năm ngày công lấy từ DB (0 = bỏ qua)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    year = args.attendance_year if args.attendance_year > 0 else None
    hien_phap = args.hien_phap.resolve()
    out_dir = (args.out or default_employee_data_dir(hien_phap)).resolve()
    run(
        hien_phap=hien_phap,
        out_dir=out_dir,
        attendance_year=year,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
