"""Bổ sung / sửa STK, lương HĐ, ngày vào, ngày ký HĐ, SĐT từ bảng lương.

Không đụng ngày sinh / CCCD / địa chỉ (nguồn đó là trich_xuat Excel).

Chỉ dry-run trừ khi có --apply. Không ghi VPS trừ khi user bảo.

  docker compose exec api python -m app.scripts.fill_bank_from_salary /tmp/salary_dir --latest --dry-run
  docker compose exec api python -m app.scripts.fill_bank_from_salary /tmp/salary_dir --latest --snapshots /tmp/snapshots --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.scripts.import_salary_employee_profile import (
    _load_records,
    _merge_latest,
    _profile_from_parsed,
)

# Không copy các trường này dù file lương / snapshot có.
FORBIDDEN_FIELDS = frozenset(
    {
        "birth_date",
        "id_number",
        "id_issue_date",
        "id_issue_place_code",
        "permanent_address",
        "temporary_address",
        "full_name",
    }
)

_DRY_RUN_SAMPLE = 40


def _dec(val: Any) -> Decimal | None:
    if val in (None, "", 0, "0", "0.0", "0.00"):
        return None
    try:
        n = Decimal(str(val))
    except Exception:
        return None
    return n if n > 0 else None


def _empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, Decimal) and val == 0:
        return True
    return False


def _fmt(val: Any) -> str:
    if _empty(val):
        return "(trống)"
    return str(val)


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


@dataclass
class FillStats:
    bank: int = 0
    pay: int = 0
    sal: int = 0
    psal: int = 0
    join: int = 0
    signed: int = 0
    phone: int = 0
    skipped: int = 0
    changes: list[str] = field(default_factory=list)

    def add(self, code: str, field: str, old: Any, new: Any) -> None:
        self.changes.append(f"  {code} {field}: {_fmt(old)} → {_fmt(new)}")

    def message(self) -> str:
        return (
            f"bank={self.bank}, pay_channel={self.pay}, luongHD={self.sal}, "
            f"luongTV={self.psal}, ngay_vao={self.join}, ky_HD={self.signed}, "
            f"sdt={self.phone}, skip={self.skipped}"
        )


def apply_profile_to_employee(emp: Any, prof: dict[str, Any], stats: FillStats) -> None:
    """Ghi STK / lương / ngày / SĐT. Không đụng ngày sinh, CCCD, địa chỉ, tên."""
    code = getattr(emp, "employee_code", "?")

    bank = prof.get("bank_account")
    if bank and emp.bank_account != bank:
        stats.add(code, "bank", emp.bank_account, bank)
        emp.bank_account = bank
        stats.bank += 1

    phone = prof.get("phone")
    if phone and not emp.phone:
        stats.add(code, "sdt", emp.phone, phone)
        emp.phone = phone
        stats.phone += 1

    sal = _dec(prof.get("contract_salary"))
    if sal is not None and emp.contract_salary != sal:
        stats.add(code, "luongHD", emp.contract_salary, sal)
        emp.contract_salary = sal
        stats.sal += 1

    psal = _dec(prof.get("probation_salary"))
    if psal is not None and _empty(emp.probation_salary):
        stats.add(code, "luongTV", emp.probation_salary, psal)
        emp.probation_salary = psal
        stats.psal += 1

    join = prof.get("join_date")
    if join and not emp.join_date:
        stats.add(code, "ngay_vao", emp.join_date, join)
        emp.join_date = join
        stats.join += 1

    signed = prof.get("contract_signed_at")
    if signed and not emp.contract_signed_at:
        stats.add(code, "ky_HD", emp.contract_signed_at, signed)
        emp.contract_signed_at = signed
        stats.signed += 1

    ch = prof.get("pay_channel")
    if ch in ("ATM", "CASH") and emp.pay_channel != ch:
        if ch == "CASH" or not emp.bank_account:
            stats.add(code, "pay_channel", emp.pay_channel, ch)
            emp.pay_channel = ch
            stats.pay += 1

    for key in FORBIDDEN_FIELDS:
        if key in prof:
            # Không gán — nguồn trich_xuat / không đụng tên.
            pass


def apply_snapshot_bank(emp: Any, bank: str, stats: FillStats) -> None:
    if emp.bank_account:
        return
    code = getattr(emp, "employee_code", "?")
    stats.add(code, "bank(snapshot)", emp.bank_account, bank)
    emp.bank_account = bank
    stats.bank += 1


def run(
    source: str,
    *,
    latest: bool = False,
    dry_run: bool = True,
    snapshots: str | None = None,
) -> FillStats:
    if latest and os.path.isdir(source):
        paths = sorted(str(p) for p in Path(source).glob("2.Salary table for *.2026.xls"))
        records = _merge_latest(paths)
    else:
        records = _load_records(source)

    snap_banks = _load_snapshot_banks(snapshots) if snapshots else {}

    stats = FillStats()
    db = SessionLocal()
    try:
        codes = set(records) | set(snap_banks)
        emps: dict[str, Employee] = {}
        if codes:
            emps = {
                e.employee_code: e
                for e in db.query(Employee).filter(Employee.employee_code.in_(codes)).all()
            }

        for msnv, rec in records.items():
            emp = emps.get(msnv)
            if emp is None:
                stats.skipped += 1
                continue
            prof = _profile_from_parsed(rec, rec.get("pay_channel"))
            apply_profile_to_employee(emp, prof, stats)

        for code, bank in snap_banks.items():
            emp = emps.get(code)
            if emp is None:
                continue
            apply_snapshot_bank(emp, bank, stats)

        print(stats.message())
        for line in stats.changes[:_DRY_RUN_SAMPLE]:
            print(line)
        extra = len(stats.changes) - _DRY_RUN_SAMPLE
        if extra > 0:
            print(f"  … và {extra} thay đổi nữa")

        if dry_run:
            db.rollback()
            print(f"DRY-RUN: sẽ bổ sung {stats.message()} — chưa ghi DB")
        else:
            db.commit()
            print(f"HOÀN TẤT: bổ sung {stats.message()}")
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--latest", action="store_true")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Không commit (mặc định nếu không có --apply)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Ghi DB — chỉ dùng khi user bảo chạy production",
    )
    p.add_argument(
        "--snapshots",
        default=None,
        help="Thư mục snapshot (employees/*.json) — chỉ lấp STK còn trống",
    )
    args = p.parse_args()
    dry_run = True
    if args.apply:
        dry_run = False
    elif args.dry_run:
        dry_run = True
    else:
        print("Chưa có --apply → chạy dry-run (không ghi DB).")
    run(
        args.source,
        latest=args.latest,
        dry_run=dry_run,
        snapshots=args.snapshots,
    )


if __name__ == "__main__":
    main()
