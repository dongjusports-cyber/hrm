"""Dựng lại cây tổ chức thật từ CSV đã trích GenusSuite.

Xóa sạch nhân viên + phiếu lương test hiện có (dữ liệu test, được phép xóa — N2),
rồi nạp:
- 10 bộ phận thật từ `TCO_EODEPT`  → departments
- 73 tổ thật từ `THR_ABWORKGRP`    → teams
- 52 chức vụ thật từ `HRAB0060`    → positions
- 82 mã công việc thật từ `HRAB0100` → jobs

Nguồn: `apps/api/data/org_structure/*.csv` (trích bằng extract_org_structure.py).
Script này CHỈ đọc CSV.

KHÔNG nạp lại nhân viên/lương ở đây.

Chạy trong container:
    docker exec djhrm-api python -m app.scripts.load_org_structure [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.attendance.models import WorkShift  # noqa: F401 — FK teams.default_shift_id
from app.modules.audit.models import AuditLog
from app.modules.core.models import User  # noqa: F401 — đăng ký bảng users cho FK audit_logs.actor_user_id
from app.modules.mdm.models import Department, Job, Position, Team

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "org_structure"

# Thứ tự XÓA phải tôn trọng FK — giống import_genussuite_2026.py.wipe_existing_data,
# thêm teams/positions/jobs (mới ở hạng mục 1.1) trước khi xóa departments.
WIPE_STATEMENTS = [
    "DELETE FROM disputes",
    "DELETE FROM payslip_adjustments",
    "DELETE FROM payslips",
    "DELETE FROM timesheet_adjustments",
    "DELETE FROM timesheet_months",
    "DELETE FROM attendance_days",
    "DELETE FROM employee_allowance_assignments",
    "DELETE FROM employee_violations",
    "DELETE FROM employee_documents",
    "UPDATE employees SET team_id = NULL, position_code = NULL, job_code = NULL",
    "DELETE FROM users WHERE role = 'worker'",
    "DELETE FROM employees",
    "DELETE FROM pay_periods WHERE year = 2026",
    "DELETE FROM teams",
    "DELETE FROM positions",
    "DELETE FROM jobs",
    "DELETE FROM departments",
]


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def _read_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Không thấy {path}. Chạy trước: python apps/api/data/org_structure/extract_org_structure.py"
        )
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def wipe(db, dry_run: bool) -> None:
    print("== Xóa dữ liệu test cũ ==")
    if dry_run:
        print("(dry-run) sẽ chạy:", *WIPE_STATEMENTS, sep="\n  - ")
        return
    for stmt in WIPE_STATEMENTS:
        db.execute(text(stmt))
    db.commit()


def load_departments(db, dry_run: bool, *, upsert: bool = False) -> dict[str, Department]:
    rows = _read_csv("departments.csv")
    print(f"== Nạp departments: {len(rows)} dòng (kỳ vọng 10) ==")
    by_pk: dict[str, Department] = {}
    for r in rows:
        if upsert and not dry_run:
            dept = db.query(Department).filter(Department.code == r["code"]).first()
            if dept is None:
                dept = Department(code=r["code"])
                db.add(dept)
            dept.name = r["name"]
            dept.name_local = r["name_local"] or r["name"]
            dept.category = "direct"
            dept.dept_type = r["dept_type"] or None
            dept.mitapro_names = [r["name"]]
            dept.effective_from = _parse_date(r["effective_from"]) or date(2007, 1, 1)
            dept.effective_to = _parse_date(r["effective_to"])
        else:
            dept = Department(
                code=r["code"],
                name=r["name"],
                name_local=r["name_local"] or r["name"],
                category="direct",
                dept_type=r["dept_type"] or None,
                mitapro_names=[r["name"]],
                effective_from=_parse_date(r["effective_from"]) or date(2007, 1, 1),
                effective_to=_parse_date(r["effective_to"]),
            )
            if not dry_run:
                db.add(dept)
        by_pk[r["pk"]] = dept
    if not dry_run:
        db.flush()
    return by_pk


def load_teams(db, dry_run: bool, dept_by_pk: dict[str, Department], *, upsert: bool = False) -> None:
    rows = _read_csv("teams.csv")
    print(f"== Nạp teams: {len(rows)} dòng (kỳ vọng 73) ==")
    missing_dept = 0
    for r in rows:
        dept = dept_by_pk.get(r["department_pk"] or "")
        if dept is None:
            missing_dept += 1
            print(f"  ! Bỏ qua tổ '{r['code']} - {r['name']}': không tìm thấy bộ phận PK={r['department_pk']}")
            continue
        if upsert and not dry_run:
            team = (
                db.query(Team)
                .filter(Team.department_id == dept.id, Team.code == r["code"])
                .first()
            )
            if team is None:
                team = Team(department_id=dept.id, code=r["code"])
                db.add(team)
            team.name = r["name"]
            team.name_local = r["name_local"] or r["name"]
            team.effective_from = _parse_date(r["effective_from"]) or date(2007, 1, 1)
            team.effective_to = _parse_date(r["effective_to"])
        else:
            team = Team(
                department_id=dept.id,
                code=r["code"],
                name=r["name"],
                name_local=r["name_local"] or r["name"],
                effective_from=_parse_date(r["effective_from"]) or date(2007, 1, 1),
                effective_to=_parse_date(r["effective_to"]),
            )
            if not dry_run:
                db.add(team)
    if missing_dept:
        print(f"  => {missing_dept} tổ bị bỏ qua vì thiếu bộ phận cha — CẦN Chủ kiểm tra lại nguồn.")
    if not dry_run:
        db.flush()


def load_common_code_table(
    db,
    dry_run: bool,
    csv_name: str,
    model,
    extra_field: str,
    *,
    upsert: bool = False,
) -> None:
    rows = _read_csv(csv_name)
    print(f"== Nạp {model.__tablename__}: {len(rows)} dòng ==")
    for r in rows:
        kwargs = {
            "code": r["code"],
            "name": r["name"],
            "name_local": r["name_local"] or r["name"],
            "sort_order": int(r["sort_order"] or 0),
            "is_active": r["is_active"] == "1",
            extra_field: r[extra_field] == "1",
        }
        if upsert and not dry_run:
            row = db.query(model).filter(model.code == r["code"]).first()
            if row is None:
                db.add(model(**kwargs))
            else:
                for key, val in kwargs.items():
                    setattr(row, key, val)
        elif not dry_run:
            db.add(model(**kwargs))
    if not dry_run:
        db.flush()


def write_audit(db, summary: str) -> None:
    db.add(
        AuditLog(
            actor_user_id=None,
            actor_username="system.load_org_structure",
            action="load_org_structure",
            entity_type="department",
            entity_id="bulk",
            summary=summary,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Chỉ đọc CSV và in ra, không ghi DB")
    parser.add_argument(
        "--skip-wipe",
        action="store_true",
        help="Không xóa NV/lương — chỉ upsert bộ phận/tổ/chức vụ/công việc từ CSV",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if not args.skip_wipe:
            wipe(db, args.dry_run)
        else:
            print("== Bỏ qua wipe — giữ nhân viên hiện có ==")
        upsert = args.skip_wipe
        dept_by_pk = load_departments(db, args.dry_run, upsert=upsert)
        load_teams(db, args.dry_run, dept_by_pk, upsert=upsert)
        load_common_code_table(
            db, args.dry_run, "positions.csv", Position, "is_management", upsert=upsert
        )
        load_common_code_table(db, args.dry_run, "jobs.csv", Job, "is_hazardous", upsert=upsert)

        if args.dry_run:
            print("\n(dry-run) không ghi DB — chạy lại không có --dry-run để nạp thật.")
            return

        summary = (
            "Nạp lại cây tổ chức thật từ GenusSuite: 10 bộ phận (TCO_EODEPT), "
            "73 tổ (THR_ABWORKGRP), 52 chức vụ (HRAB0060), 82 công việc (HRAB0100)."
        )
        if args.skip_wipe:
            summary += " Giữ nguyên nhân viên/lương (--skip-wipe)."
        else:
            summary += " Xóa sạch nhân viên/phiếu lương test cũ theo hạng mục 1.2."
        write_audit(db, summary)
        db.commit()

        print("\n== Xác nhận số dòng sau khi nạp ==")
        print("departments:", db.query(Department).count(), "(kỳ vọng 10)")
        print("teams:", db.query(Team).count(), "(kỳ vọng 73)")
        print("positions:", db.query(Position).count(), "(kỳ vọng 52)")
        print("jobs:", db.query(Job).count(), "(kỳ vọng 82)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
