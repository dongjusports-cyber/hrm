"""Lưới phép năm — live từ sổ/bảng công; file GenuSuite chỉ còn để đối chiếu trích xuất."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID
import json
import os

from sqlalchemy.orm import Session, joinedload

from app.modules.attendance.annual_leave_ledger import (
    MONTH_KEYS,
    _al_policy,
    closed_accrual_months,
    entitled_days_per_year,
    prorate_al,
    timesheet_ale_by_month_batch,
    timesheet_ale_used_ytd_batch,
)
from app.modules.mdm.models import Employee, Team
from app.modules.policy.seed_payload import default_payload

MONTHS = MONTH_KEYS
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


def snapshot_path() -> Path | None:
    env = os.environ.get("ANNUAL_LEAVE_SNAPSHOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            p = p / "employees.json"
        return p if p.is_file() else None
    candidates: list[Path] = [_API_ROOT / "data" / "annual_leave" / "employees.json"]
    al_dir = _REPO_ROOT / "Dữ liệu nhân viên" / "Phép năm GenuSuite"
    if al_dir.is_dir():
        extracts = sorted(
            al_dir.glob("trich_xuat_*/employees.json"),
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


def build_live_grid(db: Session, as_of: date | None = None) -> dict[str, Any]:
    """Lưới HR Phép năm — số live (được hưởng / hiện tại / đã dùng / còn lại). CHỈ ĐỌC."""
    as_of = as_of or date.today()
    year = as_of.year
    through = closed_accrual_months(None, as_of, year)
    base, extra_every = _al_policy(db)
    employees_orm = (
        db.query(Employee)
        .options(joinedload(Employee.team).joinedload(Team.department))
        .filter(Employee.deleted_at.is_(None), Employee.status != "resigned")
        .order_by(Employee.employee_code.asc())
        .all()
    )
    ids = [e.id for e in employees_orm]
    used_map = timesheet_ale_used_ytd_batch(db, ids, as_of)
    by_month = timesheet_ale_by_month_batch(db, ids, as_of)
    zero = Decimal("0").quantize(Q2)
    rows: list[dict[str, Any]] = []
    for emp in employees_orm:
        months = closed_accrual_months(emp.join_date, as_of, year)
        quota = Decimal(entitled_days_per_year(emp, as_of, base, extra_every)).quantize(
            Q2, rounding=ROUND_HALF_UP
        )
        curr_al = prorate_al(quota, months)
        used = used_map.get(emp.id, zero)
        remaining = (curr_al - used).quantize(Q2, rounding=ROUND_HALF_UP)
        month_vals = by_month.get(emp.id) or {k: zero for k in MONTHS}
        dept = ""
        team_name = ""
        if emp.team is not None:
            team_name = emp.team.name or ""
            if emp.team.department is not None:
                dept = emp.team.department.name or ""
        rows.append(
            {
                "employee_id": str(emp.id),
                "employee_code": emp.employee_code,
                "full_name": emp.full_name,
                "department": dept,
                "team": team_name,
                "join_date": emp.join_date.isoformat() if emp.join_date else None,
                "al_days": str(quota),
                "used": str(used),
                "unused": str(remaining),
                "accrued_months": months,
                "curr_al": str(curr_al),
                "curr_remaining": str(remaining),
                "used_by_month": {k: str(month_vals.get(k, zero)) for k in MONTHS},
            }
        )
    notes = [
        f"Được hưởng = {BASE_DAYS} ngày (NV mới), +1 mỗi đủ {EXTRA_EVERY} năm theo ngày vào. "
        f"Hiện tại = mốc × số tháng đã đóng / 12 (hết tháng {through}). "
        "Còn lại = hiện tại − đã dùng (ALE trên bảng công). Tháng đang chạy chưa cộng."
    ]
    return {
        "year": year,
        "report_date": as_of.isoformat(),
        "accrued_through_month": through,
        "source_file": None,
        "source_label": f"Sổ phép {year} · đến hết tháng {through}",
        "missing": False,
        "notes": notes,
        "employee_count": len(rows),
        "matched_in_db": len(rows),
        "employees": rows,
    }
