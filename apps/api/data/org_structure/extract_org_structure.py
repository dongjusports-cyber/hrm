# -*- coding: utf-8 -*-
"""Trích 10 bộ phận (TCO_EODEPT), 73 tổ (THR_ABWORKGRP), 52 chức vụ (HRAB0060),
82 công việc (HRAB0100) từ file gốc GenusSuite ra CSV sạch, không PII, để loader
trong container đọc (container không mount thư mục HIEN_PHAP).

Chạy MỘT LẦN trên máy host (không cần Docker) — hạng mục 1.2.
    python apps/api/data/org_structure/extract_org_structure.py
"""

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[4]  # repo root (tự nhận — .123: C:\DATA\HRM\dj-hrm\dj-hrm)
SRC = ROOT / "HIEN_PHAP" / "GenuSuite HRM"
OUT = Path(__file__).resolve().parent


def split_sql_values(s: str) -> list[str]:
    """Tách các giá trị trong `VALUES (...)` của Oracle, tôn trọng dấu nháy đơn và
    dấu ngoặc lồng (vd TO_Date('...', '...'))."""
    tokens: list[str] = []
    cur = ""
    depth = 0
    in_str = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if in_str:
            cur += c
            if c == "'":
                if i + 1 < n and s[i + 1] == "'":
                    cur += "'"
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if c == "'":
            in_str = True
            cur += c
        elif c == "(":
            depth += 1
            cur += c
        elif c == ")":
            depth -= 1
            cur += c
        elif c == "," and depth == 0:
            tokens.append(cur.strip())
            cur = ""
        else:
            cur += c
        i += 1
    if cur.strip():
        tokens.append(cur.strip())
    return tokens


def sql_str(v: str) -> str | None:
    v = v.strip()
    if v.upper() == "NULL" or v == "":
        return None
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1].replace("''", "'")
    return v


def sql_date_yyyymmdd(v: str) -> str | None:
    """ST_DATE/END_DATE của GenusSuite là chuỗi 'YYYYMMDD'. Trả về 'YYYY-MM-DD'."""
    s = sql_str(v)
    if not s or len(s) != 8 or not s.isdigit():
        return None
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def parse_inserts(text: str, table: str) -> list[list[str]]:
    pattern = re.compile(
        r"INSERT INTO\s+" + re.escape(table) + r"\s*\((?P<cols>.*?)\)\s*VALUES\s*\(\s*(?P<vals>.*?)\)\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    rows = []
    for m in pattern.finditer(text):
        rows.append(split_sql_values(m.group("vals")))
    return rows


def extract_departments() -> None:
    text = (SRC / "Org_Structure_Data..sql").read_text(encoding="utf-8", errors="replace")
    rows = parse_inserts(text, "TCO_EODEPT")
    out_rows = []
    for r in rows:
        pk, dept_id, dept_type, dept_nm, dept_lnm, dept_fnm = r[0:6]
        st_date, end_date = r[10], r[11]
        out_rows.append(
            {
                "pk": sql_str(pk),
                "code": sql_str(dept_id),
                "name": sql_str(dept_nm) or "",
                "name_local": sql_str(dept_lnm) or sql_str(dept_nm) or "",
                "dept_type": sql_str(dept_type) or "",
                "effective_from": sql_date_yyyymmdd(st_date) or "2007-01-01",
                "effective_to": sql_date_yyyymmdd(end_date),
            }
        )
    out_rows.sort(key=lambda x: x["code"])
    _write_csv(
        OUT / "departments.csv",
        ["pk", "code", "name", "name_local", "dept_type", "effective_from", "effective_to"],
        out_rows,
    )
    print(f"departments: {len(out_rows)} dòng")


def extract_teams() -> None:
    text = (SRC / "Master_Data.sql").read_text(encoding="utf-8", errors="replace")
    rows = parse_inserts(text, "THR_ABWORKGRP")
    out_rows = []
    for r in rows:
        pk, workgrp_id, workgrp_nm, workgrp_lnm, workgrp_fnm, shift_pk = r[0:6]
        st_date, end_date = r[6], r[7]
        dept_pk = r[14] if len(r) > 14 else None
        out_rows.append(
            {
                "pk": sql_str(pk),
                "code": sql_str(workgrp_id) or "",
                "name": sql_str(workgrp_nm) or "",
                "name_local": sql_str(workgrp_lnm) or sql_str(workgrp_nm) or "",
                "department_pk": sql_str(dept_pk),
                "effective_from": sql_date_yyyymmdd(st_date) or "2007-01-01",
                "effective_to": sql_date_yyyymmdd(end_date),
            }
        )
    out_rows.sort(key=lambda x: (x["department_pk"] or "", x["code"]))
    _write_csv(
        OUT / "teams.csv",
        ["pk", "code", "name", "name_local", "department_pk", "effective_from", "effective_to"],
        out_rows,
    )
    print(f"teams: {len(out_rows)} dòng")


def extract_common_codes(group_code: str, out_name: str, extra_field: str, extra_default: str) -> None:
    path = SRC / "Common_Codes.csv"
    out_rows = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for row in csv.reader(f):
            if not row or row[0].strip() != group_code:
                continue
            # group_code, group_desc, seq, code, name_en, name_vi, flag, active, ...
            seq = row[2].strip() if len(row) > 2 else "0"
            code = row[3].strip() if len(row) > 3 else ""
            name_en = row[4].strip() if len(row) > 4 else ""
            name_vi = row[5].strip() if len(row) > 5 else ""
            active = row[7].strip() if len(row) > 7 else "1"
            if not code:
                continue
            out_rows.append(
                {
                    "code": code,
                    "name": name_en or name_vi,
                    "name_local": name_vi or name_en,
                    "sort_order": seq or "0",
                    "is_active": "1" if active == "1" else "0",
                    extra_field: extra_default,
                }
            )
    _write_csv(
        OUT / out_name,
        ["code", "name", "name_local", "sort_order", "is_active", extra_field],
        out_rows,
    )
    print(f"{out_name}: {len(out_rows)} dòng")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    extract_departments()
    extract_teams()
    extract_common_codes("HRAB0060", "positions.csv", "is_management", "0")
    extract_common_codes("HRAB0100", "jobs.csv", "is_hazardous", "0")


if __name__ == "__main__":
    main()
