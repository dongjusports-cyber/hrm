"""Đọc lưới phép năm từ file trích GenuSuite — CHỈ ĐỌC, không ghi sổ.

Thứ tự tìm file:
  1. Biến ANNUAL_LEAVE_SNAPSHOT (file hoặc thư mục chứa employees.json)
  2. apps/api/data/annual_leave/employees.json  (Docker .123: /app/data/…)
  3. HIEN_PHAP/Phép năm GenuSuite/trich_xuat_*/employees.json mới nhất
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID
import calendar
import json
import os

from sqlalchemy.orm import Session

from app.modules.attendance.annual_leave_ledger import entitled_days_per_year
from app.modules.mdm.models import Employee
from app.modules.policy.seed_payload import default_payload

MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
Q2 = Decimal("0.01")
_AL_DEFAULT = default_payload()["annual_leave"]
BASE_DAYS = int(_AL_DEFAULT["days_per_year"])
EXTRA_EVERY = int(_AL_DEFAULT.get("extra_day_every_years") or 5)

_API_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _API_ROOT.parent.parent


def _as_decimal(val: Any) -> Decimal:
    if val in ("", None):
        return Decimal("0")
    return Decimal(str(val))


def _parse_iso_date(val: Any) -> date | None:
    if val in ("", None):
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    s = str(val).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def closed_accrual_months(join_date: date | None, as_of: date, year: int) -> int:
    """Số tháng đã đóng trong `year` — tháng đang chạy chưa cộng.

    VD báo cáo 17/8/2026 → hết tháng 7 → 7 tháng (16/12×7 = 9.33).
    """
    if as_of.year < year:
        return 0
    if as_of.year > year:
        through = 12
    elif as_of.day >= calendar.monthrange(as_of.year, as_of.month)[1]:
        through = as_of.month
    else:
        through = as_of.month - 1
    if through <= 0:
        return 0
    start_month = 1
    if join_date and join_date.year == year:
        start_month = join_date.month
    elif join_date and join_date.year > year:
        return 0
    months = through - start_month + 1
    return max(0, min(12, months))


def prorate_al(al_days: Decimal, months: int) -> Decimal:
    if months <= 0:
        return Decimal("0")
    return (al_days * Decimal(months) / Decimal(12)).quantize(Q2, rounding=ROUND_HALF_UP)


def snapshot_path() -> Path | None:
    env = os.environ.get("ANNUAL_LEAVE_SNAPSHOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            p = p / "employees.json"
        return p if p.is_file() else None
    candidates: list[Path] = [_API_ROOT / "data" / "annual_leave" / "employees.json"]
    hien = _REPO_ROOT / "HIEN_PHAP" / "Phép năm GenuSuite"
    if hien.is_dir():
        extracts = sorted(
            hien.glob("trich_xuat_*/employees.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        candidates.extend(extracts)
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_snapshot() -> dict[str, Any]:
    path = snapshot_path()
    if path is None:
        return {
            "year": None,
            "report_date": None,
            "source_file": None,
            "source_label": "Chưa có file trích xuất GenuSuite",
            "missing": True,
            "notes": [
                "Chạy python -m app.scripts.extract_annual_leave rồi copy employees.json vào data/annual_leave/."
            ],
            "employee_count": 0,
            "employees": [],
            "accrued_through_month": 0,
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows_in = raw.get("employees") or []
    year = raw.get("year") or date.today().year
    report_date = _parse_iso_date(raw.get("report_date"))
    as_of = report_date or date.today()
    employees: list[dict[str, Any]] = []
    for rec in rows_in:
        months_raw = rec.get("used_by_month") or {}
        used_by_month = {m: str(_as_decimal(months_raw.get(m))) for m in MONTHS}
        join_date = _parse_iso_date(rec.get("join_date"))
        genus_al = _as_decimal(rec.get("al_days"))
        used = _as_decimal(rec.get("used"))
        unused = _as_decimal(rec.get("unused"))
        months_closed = closed_accrual_months(join_date, as_of, int(year))
        quota = entitled_days_per_year(
            type("Emp", (), {"join_date": join_date})(),
            as_of,
            BASE_DAYS,
            EXTRA_EVERY,
        )
        al_days = Decimal(quota)
        curr_al = prorate_al(al_days, months_closed)
        curr_remaining = (curr_al - used).quantize(Q2, rounding=ROUND_HALF_UP)
        employees.append(
            {
                "employee_id": None,
                "employee_code": str(rec.get("employee_code") or "").strip(),
                "full_name": str(rec.get("full_name") or "").strip(),
                "department": str(rec.get("department") or "").strip(),
                "team": str(rec.get("team") or "").strip(),
                "join_date": join_date.isoformat() if join_date else None,
                "al_days": str(al_days),
                "genus_al_days": str(genus_al),
                "used": str(used),
                "unused": str(unused),
                "accrued_months": months_closed,
                "curr_al": str(curr_al),
                "curr_remaining": str(curr_remaining),
                "used_by_month": used_by_month,
            }
        )
    employees = [e for e in employees if e["employee_code"]]
    label = "GenuSuite"
    if year:
        label = f"GenuSuite {year}"
    if report_date:
        label += f" · báo cáo {report_date.isoformat()}"
    through = closed_accrual_months(None, as_of, int(year))
    notes = list(raw.get("notes") or [])
    notes.append(
        f"Được hưởng = {BASE_DAYS} ngày (NV mới), +1 mỗi đủ {EXTRA_EVERY} năm theo ngày vào. "
        f"Hiện tại = mốc × số tháng đã đóng từ ngày vào / 12 (hết tháng {through}). "
        "Còn lại = hiện tại − đã dùng. Không lấy mốc từ cột Excel GenuSuite (Excel chia tháng cho NV mới)."
    )
    return {
        "year": year,
        "report_date": report_date.isoformat() if report_date else None,
        "accrued_through_month": through,
        "source_file": str(path.resolve()),
        "source_label": label,
        "missing": False,
        "notes": notes,
        "employee_count": len(employees),
        "employees": employees,
    }


def attach_employee_ids(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = payload.get("employees") or []
    codes = [r["employee_code"] for r in rows if r.get("employee_code")]
    if not codes:
        return payload
    found = {
        e.employee_code: e.id
        for e in db.query(Employee.id, Employee.employee_code)
        .filter(Employee.employee_code.in_(codes))
        .all()
    }
    for row in rows:
        eid = found.get(row["employee_code"])
        row["employee_id"] = str(eid) if isinstance(eid, UUID) else (str(eid) if eid else None)
    payload["matched_in_db"] = sum(1 for r in rows if r.get("employee_id"))
    return payload
