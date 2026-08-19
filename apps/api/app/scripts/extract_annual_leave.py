"""Trích xuất phép năm từ Excel GenuSuite (export màn Annual Leave).

Nguồn mặc định:
  Dữ liệu nhân viên/Phép năm GenuSuite/phép năm 17.08.26.xls

Output:
  Dữ liệu nhân viên/Phép năm GenuSuite/trich_xuat_<ngày>/
    employees.json   — 1 file, mỗi NV: số ngày + dùng theo tháng
    annual_leave.csv — bảng HR (cột gần màn GenuSuite)
    manifest.json

Chạy:
  python -m app.scripts.extract_annual_leave
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import xlrd

from app.scripts.employee_data_paths import annual_leave_source_dir, repo_root
from app.scripts.import_employee_list_1108 import _parse_vn_date

SCHEMA_VERSION = 1
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def default_source_dir() -> Path:
    return annual_leave_source_dir()


def _find_xls(folder: Path) -> Path:
    files = sorted(folder.glob("*.xls"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [p for p in files if not p.name.startswith("~$")]
    if not files:
        raise FileNotFoundError(f"Không thấy file .xls trong {folder}")
    return files[0]


def _num(val: Any) -> Decimal:
    if val in ("", None, "-"):
        return Decimal("0")
    if isinstance(val, str):
        val = val.replace("\xa0", "").replace(",", "").strip()
        if not val or val == "-":
            return Decimal("0")
    return Decimal(str(val))


def _msnv(val: Any) -> str | None:
    if val in ("", None):
        return None
    try:
        return str(int(float(val)))
    except (TypeError, ValueError):
        s = str(val).strip()
        return s if s.isdigit() else None


def parse_workbook(xls_path: Path) -> tuple[int, date | None, list[dict[str, Any]]]:
    wb = xlrd.open_workbook(str(xls_path))
    sh = wb.sheet_by_index(0)
    year = 2026
    title = str(sh.cell_value(1, 0) or "")
    m = re.search(r"(20\d{2})", title)
    if m:
        year = int(m.group(1))
    report_date = None
    report_raw = str(sh.cell_value(3, 0) or "")
    dm = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", report_raw)
    if dm:
        report_date = _parse_vn_date(dm.group(1), 0)

    header_row = None
    for r in range(min(15, sh.nrows)):
        row0 = str(sh.cell_value(r, 0) or "").strip().upper()
        if row0 == "NO":
            header_row = r
            break
    if header_row is None:
        raise ValueError("Không thấy dòng tiêu đề NO / Emp_ID")

    rows: list[dict[str, Any]] = []
    for r in range(header_row + 1, sh.nrows):
        first = sh.cell_value(r, 0)
        if isinstance(first, str) and first.upper().startswith("TOTAL"):
            break
        code = _msnv(sh.cell_value(r, 3))
        name = str(sh.cell_value(r, 4) or "").strip()
        if not code or not name:
            continue
        used_by_month = {MONTHS[i]: _num(sh.cell_value(r, 7 + i)) for i in range(12)}
        used_months = sum(used_by_month.values(), Decimal("0"))
        unused = _num(sh.cell_value(r, 19))
        used = _num(sh.cell_value(r, 20))
        entitled = _num(sh.cell_value(r, 21))
        rows.append(
            {
                "employee_code": code,
                "row_index": r + 1,
                "department": str(sh.cell_value(r, 1) or "").strip(),
                "team": str(sh.cell_value(r, 2) or "").strip(),
                "full_name": name,
                "join_date": _parse_vn_date(sh.cell_value(r, 5), wb.datemode),
                "salary": _num(sh.cell_value(r, 6)),
                "year": year,
                "used_by_month": used_by_month,
                "used_from_months": used_months,
                "used": used,
                "unused": unused,
                "al_days": entitled,
                "al_amount": _num(sh.cell_value(r, 22)),
                "used_mismatch": used != used_months,
            }
        )
    return year, report_date, rows


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(type(obj))


def run(xls_path: Path, out_dir: Path) -> dict[str, Any]:
    year, report_date, rows = parse_workbook(xls_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_sorted = sorted(rows, key=lambda x: x["employee_code"])

    payload = {
        "schema_version": SCHEMA_VERSION,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(xls_path.resolve()),
        "report_date": report_date.isoformat() if report_date else None,
        "year": year,
        "employee_count": len(rows_sorted),
        "ui_columns_not_in_excel": ["AL_LastYear", "Curr_AL", "Cur_BAL"],
        "notes": [
            "File Excel GenuSuite: tháng 1–12 + Unused / Used / Annual Leave / AL Amount.",
            "Màn Annual Leave còn AL_LastYear, Curr_AL, Cur_BAL — không có trong file export này.",
            "al_days = Annual Leave; used = Used Leave; unused = Unused Leave.",
        ],
        "employees": rows_sorted,
    }
    (out_dir / "employees.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    csv_path = out_dir / "annual_leave.csv"
    fieldnames = [
        "employee_code",
        "full_name",
        "department",
        "team",
        "join_date",
        "al_days",
        "used",
        "unused",
        *MONTHS,
        "al_amount",
        "salary",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for rec in rows_sorted:
            row = {
                "employee_code": rec["employee_code"],
                "full_name": rec["full_name"],
                "department": rec["department"],
                "team": rec["team"],
                "join_date": rec["join_date"].isoformat() if rec["join_date"] else "",
                "al_days": rec["al_days"],
                "used": rec["used"],
                "unused": rec["unused"],
                "al_amount": rec["al_amount"],
                "salary": rec["salary"],
            }
            row.update(rec["used_by_month"])
            w.writerow(row)

    mismatch = sum(1 for r in rows_sorted if r["used_mismatch"])
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "extracted_at": payload["extracted_at"],
        "source_file": payload["source_file"],
        "report_date": payload["report_date"],
        "year": year,
        "employee_count": len(rows_sorted),
        "used_vs_months_mismatch": mismatch,
        "files": {
            "employees_json": "employees.json",
            "csv": "annual_leave.csv",
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    api_copy = repo_root() / "apps" / "api" / "data" / "annual_leave"
    api_copy.mkdir(parents=True, exist_ok=True)
    (api_copy / "employees.json").write_text(
        (out_dir / "employees.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    manifest["api_copy"] = str(api_copy / "employees.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xls", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    folder = default_source_dir()
    xls = (args.xls or _find_xls(folder)).resolve()
    stamp = datetime.now().strftime("%d%m%y")
    out = (args.out or (folder / f"trich_xuat_{stamp}")).resolve()
    man = run(xls, out)
    print(f"Nguồn: {xls}")
    print(f"Output: {out}")
    print(f"NV: {man['employee_count']} | lệch Used vs tổng tháng: {man['used_vs_months_mismatch']}")
    if man.get("api_copy"):
        print(f"API .123: {man['api_copy']}")


if __name__ == "__main__":
    main()
