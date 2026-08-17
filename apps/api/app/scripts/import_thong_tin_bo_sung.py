"""Nạp Thông tin bổ sung 14.08 vào DB (không xóa NV, không đè STK/BHXH đã đúng).

  python -m app.scripts.import_thong_tin_bo_sung
  python -m app.scripts.import_thong_tin_bo_sung --xlsx /tmp/bo_sung.xlsx --dry-run
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.attendance.models import WorkShift  # noqa: F401
from app.modules.mdm.models import Employee
from app.modules.payroll.models import EmployeeAllowanceAssignment, PayComponent
from app.modules.payroll.seed_allowances import seed_allowance_types
from app.scripts.thong_tin_bo_sung import (
    DEFAULT_ETHNICITY,
    DEFAULT_NATIONALITY,
    DEFAULT_RELIGION,
    MANAGED_ALLOWANCE_CODES,
    SKIP_TEST_CODES,
    apply_supplement_to_employee,
    default_xlsx_path,
    load_supplement,
)


def _apply_identity(emp: Employee) -> list[str]:
    changed: list[str] = []
    for field, val in (
        ("nationality_code", DEFAULT_NATIONALITY),
        ("ethnicity_code", DEFAULT_ETHNICITY),
        ("religion_code", DEFAULT_RELIGION),
    ):
        if getattr(emp, field, None) != val:
            setattr(emp, field, val)
            changed.append(field)
    return changed


def _sync_allowances(
    db,
    emp: Employee,
    amounts: dict[str, Decimal],
    type_by_code: dict[str, PayComponent],
) -> int:
    n = 0
    for code in MANAGED_ALLOWANCE_CODES:
        at = type_by_code.get(code)
        if at is None:
            continue
        amt = amounts.get(code) or Decimal("0")
        row = (
            db.query(EmployeeAllowanceAssignment)
            .filter(
                EmployeeAllowanceAssignment.employee_id == emp.id,
                EmployeeAllowanceAssignment.allowance_type_id == at.id,
            )
            .one_or_none()
        )
        if amt <= 0:
            if row is not None:
                db.delete(row)
                n += 1
            continue
        if row is None:
            db.add(
                EmployeeAllowanceAssignment(
                    employee_id=emp.id,
                    allowance_type_id=at.id,
                    amount=amt,
                )
            )
            n += 1
        elif row.amount != amt:
            row.amount = amt
            n += 1
    return n


def run(xlsx: Path, *, dry_run: bool = False) -> None:
    records = load_supplement(xlsx)
    print(f"Đọc {len(records)} MSNV từ {xlsx.name}")
    db = SessionLocal()
    updated = skipped = missing = 0
    field_hits: dict[str, int] = {}
    try:
        seed_allowance_types(db)
        type_by_code = {t.code: t for t in db.query(PayComponent).all()}

        for emp in db.query(Employee).filter(Employee.deleted_at.is_(None)).all():
            if emp.employee_code in SKIP_TEST_CODES:
                continue
            for f in _apply_identity(emp):
                field_hits[f] = field_hits.get(f, 0) + 1

        for code, rec in sorted(records.items()):
            if code in SKIP_TEST_CODES:
                skipped += 1
                continue
            emp = db.query(Employee).filter(Employee.employee_code == code, Employee.deleted_at.is_(None)).first()
            if emp is None:
                missing += 1
                continue
            changed = apply_supplement_to_employee(emp, rec)
            amounts = rec.get("allowance_amounts")
            if amounts:
                if _sync_allowances(db, emp, amounts, type_by_code):
                    changed.append("allowances")
            if changed:
                updated += 1
                for f in changed:
                    field_hits[f] = field_hits.get(f, 0) + 1
        if dry_run:
            db.rollback()
            print("(dry-run) không ghi DB.")
        else:
            db.commit()
        print(f"Cập nhật {updated} NV | không có trong DB {missing} | bỏ qua test {skipped}")
        if field_hits:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(field_hits.items(), key=lambda x: -x[1]))
            print(f"  Trường: {summary}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp Thông tin bổ sung vào DB")
    parser.add_argument("--xlsx", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    xlsx = (args.xlsx or default_xlsx_path()).resolve()
    run(xlsx, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
