"""Cập nhật hồ sơ nhân viên từ bảng lương GenusSuite (.xls).

File lương chứa: MSNV, họ tên, CMND/CCCD, Số TK (hoặc SĐT nếu 10 số), tổ, chức vụ,
ngày vào, ngày ký HĐ, lương TV/HĐ, giới tính, kênh trả (ATM/CASH).

Ngày sinh suy từ 12 số CCCD (năm + tháng/ngày = 01/01 nếu không có nguồn khác).
File lương KHÔNG có địa chỉ — cần nguồn THR_ABEMP riêng nếu có sau.

Chạy (Docker):
  docker cp "C:/DATA/HRM/dj-hrm/dj-hrm/HIEN_PHAP/Salary/2.Salary table for July.2026.xls" djhrm-api:/tmp/salary.xls
  docker compose exec api python -m app.scripts.import_salary_employee_profile /tmp/salary.xls

  # Hoặc cả thư mục — lấy bản ghi mới nhất theo MSNV (tháng 7 thắng):
  docker compose exec api python -m app.scripts.import_salary_employee_profile /tmp/salary_dir --latest
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from calendar import monthrange
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.modules.mdm.models import Employee
from app.scripts import import_genussuite_2026 as gs


def _clean_id(raw: Any) -> str | None:
    if raw in ("", None):
        return None
    s = re.sub(r"\D", "", str(raw).strip())
    return s or None


def _split_bank_phone(raw: Any) -> tuple[str | None, str | None]:
    if raw in ("", None):
        return None, None
    s = re.sub(r"\D", "", str(raw).strip())
    if not s:
        return None, None
    if len(s) <= 11 and s.startswith("0"):
        return None, s
    if len(s) >= 12:
        return s, None
    return s, None


def _gender_from_sex(sex: str | None) -> str | None:
    if not sex:
        return None
    t = unicodedata.normalize("NFC", str(sex)).strip().lower()
    if t in ("m", "f", "male", "female"):
        return "M" if t in ("m", "male") else "F"
    if "nam" in t:
        return "M"
    if t.startswith("n") or "nữ" in t or "nu" in t:
        return "F"
    return None


def _birth_from_cccd(id_number: str | None) -> date | None:
    """Suy năm sinh từ CCCD 12 số (ngày/tháng không có trong file lương)."""
    if not id_number or len(id_number) != 12:
        return None
    try:
        g = int(id_number[3])
        yy = int(id_number[4:6])
    except ValueError:
        return None
    if g in (0, 2, 4, 6):
        year = 1900 + yy
    elif g in (1, 3, 5, 7):
        year = 2000 + yy
    else:
        year = 1900 + yy
    if year > date.today().year - 16:
        year = 1900 + yy
    if not (1945 <= year <= date.today().year - 16):
        return None
    return date(year, 1, 1)


def _profile_from_parsed(rec: dict[str, Any], pay_channel: str | None) -> dict[str, Any]:
    id_number = _clean_id(rec.get("id_number"))
    bank, phone = _split_bank_phone(rec.get("bank_account"))
    gender = _gender_from_sex(rec.get("sex"))
    birth = _birth_from_cccd(id_number)
    out: dict[str, Any] = {
        "full_name": rec["name"],
        "gender": gender,
        "id_number": id_number,
        "bank_account": bank,
        "phone": phone,
        "position_title": rec.get("position") or None,
        "join_date": rec.get("join_date"),
        "contract_signed_at": rec.get("contract_signed_at"),
        "probation_salary": rec.get("probation_salary") or Decimal("0"),
        "contract_salary": rec.get("contract_salary") or Decimal("0"),
        "team_name": rec.get("dept"),
    }
    if birth:
        out["birth_date"] = birth
    if pay_channel in ("ATM", "CASH"):
        out["pay_channel"] = pay_channel
    return out


def _load_records(path: str) -> dict[str, dict[str, Any]]:
    records = gs.parse_month(path)
    atm_path = cash_path = path
    for msnv in list(records.keys()):
        ch = gs._pay_channel_for(msnv, atm_path, cash_path)
        records[msnv]["pay_channel"] = ch
    return records


MONTH_ORDER = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "June": 6,
    "July": 7,
}


def _month_key(path: str) -> int:
    name = Path(path).name
    for tag, num in MONTH_ORDER.items():
        if tag in name:
            return num
    return 0


def _merge_latest(paths: list[str]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in sorted(paths, key=_month_key):
        for msnv, rec in _load_records(path).items():
            rec = dict(rec)
            rec["_source_month"] = _month_key(path)
            merged[msnv] = rec
    return merged


def run(
    source: str,
    *,
    latest: bool = False,
    dry_run: bool = False,
    record_date: date | None = None,
) -> None:
    if latest and os.path.isdir(source):
        paths = sorted(
            str(p)
            for p in Path(source).glob("2.Salary table for *.2026.xls")
        )
        if not paths:
            raise FileNotFoundError(f"Không có file lương .xls trong {source}")
        print(f"Đọc {len(paths)} file — mỗi MSNV lấy bản ghi tháng mới nhất.")
        records = _merge_latest(paths)
    else:
        if not os.path.isfile(source):
            raise FileNotFoundError(source)
        records = _load_records(source)
        month_num = _month_key(source) or 7
        for rec in records.values():
            rec["_source_month"] = month_num

    print(f"Tổng {len(records)} nhân viên trong file lương.")

    if dry_run:
        sample = list(records.items())[:5]
        for msnv, rec in sample:
            prof = _profile_from_parsed(rec, rec.get("pay_channel"))
            print(f"  {msnv}: {prof['full_name']} | CCCD={prof.get('id_number')} | phone={prof.get('phone')} | bank={prof.get('bank_account')} | birth={prof.get('birth_date')}")
        print("DRY-RUN — không ghi DB.")
        return

    db = SessionLocal()
    try:
        team_by_name = gs.prepare_org_structure(db)

        updated = created = 0
        no_team: list[str] = []

        for msnv, rec in records.items():
            prof = _profile_from_parsed(rec, rec.get("pay_channel"))
            month_num = int(rec.get("_source_month") or 7)
            emp_ref = date(2026, month_num, monthrange(2026, month_num)[1])
            team = gs.resolve_team_for(team_by_name, prof.pop("team_name", ""), emp_ref)
            if team is None:
                no_team.append(f"{msnv} ({prof['full_name']}) → {rec.get('dept')}")

            emp = db.query(Employee).filter(Employee.employee_code == msnv).first()
            if emp is None:
                emp = Employee(employee_code=msnv, status="active")
                db.add(emp)
                created += 1
            else:
                updated += 1
                emp.deleted_at = None

            for key, val in prof.items():
                if key in ("bank_account", "phone"):
                    setattr(emp, key, val)
                elif val is not None and val != "":
                    setattr(emp, key, val)
            if team is not None:
                emp.team_id = team.id

        db.commit()
        print(f"HOÀN TẤT: cập nhật {updated}, tạo mới {created}.")
        if no_team:
            print(f"  ! {len(no_team)} NV không ánh xạ được tổ:")
            for line in no_team[:15]:
                print("    -", line)
            if len(no_team) > 15:
                print(f"    ... và {len(no_team) - 15} dòng khác.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp hồ sơ NV từ bảng lương GenusSuite (.xls)")
    parser.add_argument(
        "source",
        help="Đường dẫn file .xls hoặc thư mục chứa các file lương 2026",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Nếu source là thư mục: gộp tất cả tháng, MSNV lấy bản ghi file cuối",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.source, latest=args.latest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
