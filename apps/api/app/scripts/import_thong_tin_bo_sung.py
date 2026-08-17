"""Nạp Thông tin bổ sung 14.08 vào DB (không xóa NV, không đè STK/BHXH đã đúng).

  python -m app.scripts.import_thong_tin_bo_sung
  python -m app.scripts.import_thong_tin_bo_sung --xlsx /tmp/bo_sung.xlsx --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.scripts.thong_tin_bo_sung import (
    SKIP_TEST_CODES,
    apply_supplement_to_employee,
    default_xlsx_path,
    load_supplement,
)


def run(xlsx: Path, *, dry_run: bool = False) -> None:
    records = load_supplement(xlsx)
    print(f"Đọc {len(records)} MSNV từ {xlsx.name}")
    db = SessionLocal()
    updated = skipped = missing = 0
    field_hits: dict[str, int] = {}
    try:
        for code, rec in sorted(records.items()):
            if code in SKIP_TEST_CODES:
                skipped += 1
                continue
            emp = db.query(Employee).filter(Employee.employee_code == code, Employee.deleted_at.is_(None)).first()
            if emp is None:
                missing += 1
                continue
            changed = apply_supplement_to_employee(emp, rec)
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
