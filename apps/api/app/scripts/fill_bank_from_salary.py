"""Bổ sung / sửa STK, lương HĐ, ngày vào, ngày ký HĐ từ bảng lương.

Không đụng ngày sinh / CCCD / địa chỉ (nguồn đó là trich_xuat Excel).

  docker compose exec api python -m app.scripts.fill_bank_from_salary /tmp/salary_dir --latest
  docker compose exec api python -m app.scripts.fill_bank_from_salary /tmp/salary_dir --latest --snapshots /tmp/snapshots
"""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.scripts.import_salary_employee_profile import (
    _load_records,
    _merge_latest,
    _profile_from_parsed,
)


def _dec(val) -> Decimal | None:
    if val in (None, "", 0, "0", "0.0", "0.00"):
        return None
    try:
        n = Decimal(str(val))
    except Exception:
        return None
    return n if n > 0 else None


def _load_snapshot_banks(snapshots_dir: str) -> dict[str, str]:
    root = Path(snapshots_dir)
    emp_dir = root / "employees" if (root / "employees").is_dir() else root
    out: dict[str, str] = {}
    for path in emp_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        code = str(data.get("employee_code") or path.stem).strip()
        bank = (data.get("profile") or {}).get("bank_account")
        if code and bank:
            out[code] = str(bank).strip()
    return out


def run(
    source: str,
    *,
    latest: bool = False,
    dry_run: bool = False,
    snapshots: str | None = None,
) -> None:
    if latest and os.path.isdir(source):
        paths = sorted(str(p) for p in Path(source).glob("2.Salary table for *.2026.xls"))
        records = _merge_latest(paths)
    else:
        records = _load_records(source)

    snap_banks = _load_snapshot_banks(snapshots) if snapshots else {}

    db = SessionLocal()
    filled_bank = filled_pay = filled_sal = filled_join = filled_signed = filled_phone = skipped = 0
    try:
        for msnv, rec in records.items():
            prof = _profile_from_parsed(rec, rec.get("pay_channel"))
            emp = db.query(Employee).filter(Employee.employee_code == msnv).first()
            if emp is None:
                skipped += 1
                continue

            bank = prof.get("bank_account")
            if bank and emp.bank_account != bank:
                emp.bank_account = bank
                filled_bank += 1

            phone = prof.get("phone")
            if phone and not emp.phone:
                emp.phone = phone
                filled_phone += 1

            sal = _dec(prof.get("contract_salary"))
            if sal is not None and emp.contract_salary != sal:
                emp.contract_salary = sal
                filled_sal += 1

            psal = _dec(prof.get("probation_salary"))
            if psal is not None and not emp.probation_salary:
                emp.probation_salary = psal

            join = prof.get("join_date")
            if join and not emp.join_date:
                emp.join_date = join
                filled_join += 1

            signed = prof.get("contract_signed_at")
            if signed and not emp.contract_signed_at:
                emp.contract_signed_at = signed
                filled_signed += 1

            ch = prof.get("pay_channel")
            if ch in ("ATM", "CASH") and emp.pay_channel != ch:
                if ch == "CASH" or not emp.bank_account:
                    emp.pay_channel = ch
                    filled_pay += 1

        for code, bank in snap_banks.items():
            emp = db.query(Employee).filter(Employee.employee_code == code).first()
            if emp is None or emp.bank_account:
                continue
            emp.bank_account = bank
            filled_bank += 1

        msg = (
            f"bank={filled_bank}, pay_channel={filled_pay}, luongHD={filled_sal}, "
            f"ngay_vao={filled_join}, ky_HD={filled_signed}, sdt={filled_phone}, skip={skipped}"
        )
        if dry_run:
            db.rollback()
            print(f"DRY-RUN: sẽ bổ sung {msg}")
        else:
            db.commit()
            print(f"HOÀN TẤT: bổ sung {msg}")
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
    p.add_argument(
        "--snapshots",
        default=None,
        help="Thư mục snapshot (employees/*.json) — chỉ lấp STK còn trống",
    )
    args = p.parse_args()
    run(
        args.source,
        latest=args.latest,
        dry_run=args.dry_run,
        snapshots=args.snapshots,
    )


if __name__ == "__main__":
    main()
