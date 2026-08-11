"""Chỉ bổ sung bank_account / pay_channel từ file lương — không đụng tên, ngày sinh, tổ.

  docker compose exec api python -m app.scripts.fill_bank_from_salary /tmp/salary_dir --latest
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.scripts.import_salary_employee_profile import (
    _merge_latest,
    _load_records,
    _profile_from_parsed,
)


def run(source: str, *, latest: bool = False, dry_run: bool = False) -> None:
    if latest and os.path.isdir(source):
        paths = sorted(str(p) for p in Path(source).glob("2.Salary table for *.2026.xls"))
        records = _merge_latest(paths)
    else:
        records = _load_records(source)

    db = SessionLocal()
    filled_bank = filled_pay = skipped = 0
    try:
        for msnv, rec in records.items():
            prof = _profile_from_parsed(rec, rec.get("pay_channel"))
            emp = db.query(Employee).filter(Employee.employee_code == msnv).first()
            if emp is None:
                skipped += 1
                continue
            bank = prof.get("bank_account")
            if bank and not emp.bank_account:
                emp.bank_account = bank
                filled_bank += 1
            ch = prof.get("pay_channel")
            if ch in ("ATM", "CASH") and emp.pay_channel != ch:
                # chỉ set khi đang mặc định ATM và file nói CASH, hoặc bank trống → CASH
                if ch == "CASH" or not emp.bank_account:
                    emp.pay_channel = ch
                    filled_pay += 1
        if dry_run:
            db.rollback()
            print(f"DRY-RUN: sẽ bổ sung bank={filled_bank}, pay_channel={filled_pay}, skip={skipped}")
        else:
            db.commit()
            print(f"HOÀN TẤT: bổ sung bank={filled_bank}, pay_channel={filled_pay}, skip={skipped}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--latest", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    run(args.source, latest=args.latest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
