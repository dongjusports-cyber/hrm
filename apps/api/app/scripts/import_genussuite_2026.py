"""Nạp dữ liệu lương thật Jan-Jul/2026 từ export GenusSuite (Dữ liệu nhân viên/Salary).

Chạy: python -m app.scripts.import_genussuite_2026 [--dry-run]

Nạp lương với ánh xạ tổ đúng, dùng cây tổ chức thật (10 departments, 73 teams),
không tự tạo Department giả từ tên trong file lương.

Chiến lược (đã chốt với người dùng):
- "Đông cứng" số liệu GenusSuite làm phiếu lương lịch sử đã phát hành (KHÔNG bắt
  Payroll Engine tính lại) — an toàn, đúng số thật.
- NV biến mất khỏi bảng lương 1+ tháng rồi QUAY LẠI trước tháng 7 → ghi audit log
  "nghỉ thai sản/nghỉ dài", trạng thái hiện tại = active.
- NV biến mất và KHÔNG quay lại tính đến tháng 7 → status = resigned, resign_date
  = ngày cuối tháng cuối họ còn xuất hiện.
- Tháng 7: 12 dây chuyền Line 1-12 + Sub-Sewing (team thật, cây Sewing) đóng
  effective_to = 2026-06-30 — export THR_ABWORKGRP gốc CHƯA có ngày đóng này nên
  ta tự bổ sung. 5 tổ mới (Sewing CB 1/2/3, Sewing ACC, Bond Top) đã có ngày mở
  thật trong THR_ABWORKGRP (2026-07-08 / 2026-07-11) — GIỮ nguyên, không sửa
  thành 2026-07-01 như bản nháp lộ trình vì có ngày thật rồi (file gốc > kế hoạch
  khi kế hoạch chỉ là suy đoán, còn file gốc là dữ kiện — xem báo cáo phiên 1.3).
- Tên bộ phận trong file lương là TÊN TỔ (Team), không phải tên Bộ phận (Department)
  cấp cao — vd "Line 1", "Sewing ACC", "Accounting" đều là tổ. Ánh xạ theo tên tổ,
  suy ra department_id từ team.department_id.
- CMND + số tài khoản ngân hàng → che 4-6 số giữa trước khi lưu (PII thật).
- Xoá dữ liệu nhân sự/lương test cũ trước khi nạp — KHÔNG xoá departments/teams/
  positions/jobs (đó là cây tổ chức thật, không phải dữ liệu test).
"""

from __future__ import annotations

import argparse
import os
import sys
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import xlrd

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.worker.service import default_worker_password
from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.audit.models import AuditLog
from app.modules.core.models import User
from app.modules.mdm.models import Employee, Team
from app.modules.payroll.models import Payslip
from app.scripts.employee_data_paths import salary_dir


def _salary_data_dir() -> str:
    """Bảng lương Excel — `Dữ liệu nhân viên/Salary` (Docker: docker cp → /tmp/salary_dir)."""
    candidates = [
        salary_dir(),
        Path("/tmp/salary_dir"),
        Path(__file__).resolve().parents[2] / "data" / "genussuite_2026",
    ]
    for folder in candidates:
        if folder.is_dir() and any(folder.glob("2.Salary table for *.xls")):
            return str(folder)
    return str(salary_dir())


DATA_DIR = _salary_data_dir()

MONTHS = [
    (1, "Jan"),
    (2, "Feb"),
    (3, "Mar"),
    (4, "Apr"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
]

# 13 tổ (team.name thật, cây Sewing) ngưng dùng từ 2026-07 — export THR_ABWORKGRP
# gốc chưa có ngày đóng nên script này tự bổ sung effective_to (hạng mục 1.3).
LEGACY_SEWING_TEAM_NAMES = {
    "Line 1", "Line 2", "Line 3", "Line 4", "Line 5", "Line 6", "Line 7",
    "Line 8", "Line 9", "Line 10", "Line 11", "Line 12", "Sub-Sewing",
}
LEGACY_SEWING_CLOSE_DATE = date(2026, 6, 30)

# Tên tổ trùng ở ≥2 bộ phận (dữ liệu thật THR_ABWORKGRP) — không đủ thông tin trong
# file lương để phân biệt, nên chọn theo quy tắc CỐ ĐỊNH: tổ mở SAU (effective_from
# lớn hơn) thắng, vì phản ánh cách tổ chức mới nhất. Ghi rõ trong báo cáo phiên 1.3
# để Chủ chỉnh lại qua Admin (employee_assignments, hạng mục 1.5) nếu chọn sai.
AMBIGUOUS_TEAM_NAMES = {"Bond Top", "QA", "Warehouse"}


def _mask_middle(value: str | None, keep: int = 3) -> str | None:
    if not value:
        return value
    v = value.strip()
    if len(v) <= keep * 2:
        return v[:1] + "*" * max(len(v) - 1, 0)
    return v[:keep] + "*" * (len(v) - keep * 2) + v[-keep:]


def _parse_vn_date(raw: Any) -> date | None:
    if raw in ("", None):
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None
    if isinstance(raw, (int, float)):
        try:
            dt = xlrd.xldate_as_datetime(raw, 0)
            return dt.date()
        except Exception:
            return None
    return None


def _num(raw: Any) -> Decimal:
    if raw in ("", None):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:
        return Decimal("0")


def _main_sheet(wb: xlrd.book.Book):
    for name in ("TOTAL", "Total", "total"):
        if name in wb.sheet_names():
            return wb.sheet_by_name(name)
    return wb.sheet_by_index(0)


def _find_header_row(sheet) -> int | None:
    for r in range(min(20, sheet.nrows)):
        v0 = sheet.cell_value(r, 0)
        if isinstance(v0, str) and v0.strip().lower() == "stt":
            return r
    return None


def _find_gross_col(sheet, hdr: int) -> int:
    """Dò cột 'GROSS SALARY' theo header tiếng Anh — không dựa vào ncols vì có
    file thừa cột helper/blank ở giữa hoặc cuối (37/38 cột lệch nhau tuỳ tháng)."""
    for r in range(max(0, hdr - 3), hdr):
        for c in range(sheet.ncols):
            v = sheet.cell_value(r, c)
            if isinstance(v, str) and v.strip().upper().startswith("GROSS"):
                return c
    raise RuntimeError("Không tìm thấy cột GROSS SALARY")


def parse_month(path: str) -> dict[str, dict[str, Any]]:
    """Trả về {msnv: record} cho 1 tháng — record đã map field theo tên rõ nghĩa."""
    wb = xlrd.open_workbook(path)
    sheet = _main_sheet(wb)
    hdr = _find_header_row(sheet)
    if hdr is None:
        raise RuntimeError(f"Không tìm thấy dòng header 'Stt' trong {path}")
    # Khối đầu (0..28) ổn định ở mọi file. Khối cuối (Gross,SI,HI,UI,UN,Deduct,
    # NET,SEX — 8 cột) định vị bằng chính header "GROSS SALARY", vì số cột vật lý
    # (ncols) lệch nhau giữa các tháng do cột helper/blank khác nhau.
    back_start = _find_gross_col(sheet, hdr)

    records: dict[str, dict[str, Any]] = {}
    for r in range(hdr + 1, sheet.nrows):
        msnv_raw = sheet.cell_value(r, 2)
        name_raw = sheet.cell_value(r, 3)
        if isinstance(name_raw, float) or not isinstance(name_raw, str) or not name_raw.strip():
            continue
        try:
            msnv_num = int(float(msnv_raw))
        except (TypeError, ValueError):
            continue
        if msnv_num < 1000:  # loại dòng số thứ tự cột giả (1,2,3..38) lẫn vào bảng
            continue
        msnv = str(msnv_num)
        dept = str(sheet.cell_value(r, 1)).strip()
        if not dept or dept.replace(".", "").isdigit():
            continue

        back = [sheet.cell_value(r, back_start + i) for i in range(8)]
        records[msnv] = {
            "dept": dept,
            "name": name_raw.strip(),
            "id_number": str(sheet.cell_value(r, 4)).strip(),
            "bank_account": str(sheet.cell_value(r, 5)).strip(),
            "position": str(sheet.cell_value(r, 7)).strip(),
            "join_date": _parse_vn_date(sheet.cell_value(r, 8)),
            "contract_signed_at": _parse_vn_date(sheet.cell_value(r, 9)),
            "probation_salary": _num(sheet.cell_value(r, 10)),
            "contract_salary": _num(sheet.cell_value(r, 11)),
            "workdays_total": _num(sheet.cell_value(r, 14)),
            "al_days": _num(sheet.cell_value(r, 15)),
            "rem_days": _num(sheet.cell_value(r, 16)),
            "wd_salary": _num(sheet.cell_value(r, 17)),
            "allowance_attend": _num(sheet.cell_value(r, 18)),
            "allowance_position": _num(sheet.cell_value(r, 19)),
            "allowance_toxic": _num(sheet.cell_value(r, 20)),
            "allowance_transport": _num(sheet.cell_value(r, 21)),
            "allowance_pccc_hse": _num(sheet.cell_value(r, 22)),
            "allowance_skill": _num(sheet.cell_value(r, 23)),
            "allowance_seniority": _num(sheet.cell_value(r, 24)),
            "allowance_other": _num(sheet.cell_value(r, 25)),
            "allowance_total": _num(sheet.cell_value(r, 26)),
            "ot_hours": _num(sheet.cell_value(r, 27)),
            "ot_pay": _num(sheet.cell_value(r, 28)),
            "gross": _num(back[0]),
            "bhxh": _num(back[1]),
            "bhyt": _num(back[2]),
            "bhtn": _num(back[3]),
            "union_fee": _num(back[4]),
            "deduct": _num(back[5]),
            "net": _num(back[6]),
            "sex": str(back[7]).strip(),
        }
    return records


def _pay_channel_for(msnv: str, path_atm: str | None, path_cash: str | None) -> str | None:
    for path, channel in ((path_atm, "ATM"), (path_cash, "CASH")):
        if not path or not os.path.exists(path):
            continue
        try:
            wb = xlrd.open_workbook(path)
            sheet = _main_sheet(wb)
            hdr = _find_header_row(sheet)
            if hdr is None:
                continue
            for r in range(hdr + 1, sheet.nrows):
                if str(int(float(sheet.cell_value(r, 2) or 0))) == msnv:
                    return channel
        except Exception:
            continue
    return None


def load_all_months() -> dict[int, dict[str, dict[str, Any]]]:
    by_month: dict[int, dict[str, dict[str, Any]]] = {}
    for month_num, tag in MONTHS:
        path = os.path.join(DATA_DIR, f"2.Salary table for {tag}.2026.xls")
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        by_month[month_num] = parse_month(path)
    return by_month


def classify_employees(by_month: dict[int, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Trả về {msnv: {months:[...], status, resign_date, leave_note}}."""
    all_msnv: set[str] = set()
    for recs in by_month.values():
        all_msnv |= set(recs.keys())

    result: dict[str, dict[str, Any]] = {}
    for msnv in all_msnv:
        months_present = sorted(m for m in by_month if msnv in by_month[m])
        last_month = months_present[-1]
        has_gap = any(m not in months_present for m in range(months_present[0], last_month))
        if last_month == 7:
            status = "active"
            resign_date = None
            leave_note = None
            if has_gap:
                gap_months = [m for m in range(months_present[0], 8) if m not in months_present]
                leave_note = (
                    f"Vắng bảng lương GenusSuite tháng {min(gap_months)}-{max(gap_months)}/2026 "
                    "rồi đi làm lại — nghi nghỉ thai sản/nghỉ dài (suy luận tự động khi nạp dữ liệu)."
                )
        else:
            status = "resigned"
            last_day = monthrange(2026, last_month)[1]
            resign_date = date(2026, last_month, last_day)
            leave_note = None
        result[msnv] = {
            "months_present": months_present,
            "last_month": last_month,
            "status": status,
            "resign_date": resign_date,
            "leave_note": leave_note,
        }
    return result


def wipe_existing_data(db) -> None:
    """Xoá nhân sự/lương test cũ. KHÔNG xoá departments/teams/positions/jobs — đó là
    cây tổ chức thật nạp ở hạng mục 1.2, không phải dữ liệu test."""
    statements = [
        "DELETE FROM disputes",
        "DELETE FROM payslip_adjustments",
        "DELETE FROM payslips",
        "DELETE FROM timesheet_adjustments",
        "DELETE FROM timesheet_months",
        "DELETE FROM attendance_days",
        "DELETE FROM employee_allowance_assignments",
        "DELETE FROM employee_violations",
        "DELETE FROM employee_documents",
        "DELETE FROM users WHERE role = 'worker'",
        "DELETE FROM employees",
        "DELETE FROM pay_periods WHERE year = 2026",
    ]
    for stmt in statements:
        db.execute(__import__("sqlalchemy").text(stmt))
    db.commit()


def prepare_org_structure(db) -> dict[str, list[Team]]:
    """Chuẩn bị cây tổ chức thật (đã nạp ở 1.2) để ánh xạ nhân viên:
    1. Dọn khoảng trắng dư trong tên tổ (lỗi nhập liệu gốc THR_ABWORKGRP: 'Line 5 ').
    2. Đóng 13 tổ Sewing cũ (Line 1-12 + Sub-Sewing) tại 2026-06-30 — export gốc
       chưa có ngày đóng này.
    3. Trả về chỉ mục tên tổ -> danh sách Team (để resolve_team_for tra theo ngày).
    """
    teams = db.query(Team).all()
    if not teams:
        raise RuntimeError(
            "Chưa có teams trong DB. Chạy trước: "
            "docker exec djhrm-api python -m app.scripts.load_org_structure (hạng mục 1.2)."
        )

    for t in teams:
        if t.name != t.name.strip():
            t.name = t.name.strip()
        if t.name_local != t.name_local.strip():
            t.name_local = t.name_local.strip()

    n_closed = 0
    for t in teams:
        if t.name in LEGACY_SEWING_TEAM_NAMES and t.effective_to is None:
            t.effective_to = LEGACY_SEWING_CLOSE_DATE
            n_closed += 1
    db.flush()
    print(f"  Đóng {n_closed} tổ Sewing cũ (Line 1-12 + Sub-Sewing) tại {LEGACY_SEWING_CLOSE_DATE}.")

    by_name: dict[str, list[Team]] = {}
    for t in teams:
        by_name.setdefault(t.name, []).append(t)
    return by_name


def resolve_team_for(by_name: dict[str, list[Team]], dept_name: str, record_date: date) -> Team | None:
    """Chọn Team đúng cho một dòng lương, theo tên + còn hiệu lực tại record_date.
    Nếu tên trùng ở ≥2 bộ phận (AMBIGUOUS_TEAM_NAMES) → chọn tổ mở SAU (xem ghi chú
    ở đầu file)."""
    candidates = by_name.get(dept_name, [])
    valid = [
        t
        for t in candidates
        if t.effective_from <= record_date and (t.effective_to is None or t.effective_to >= record_date)
    ]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    valid.sort(key=lambda t: t.effective_from, reverse=True)
    return valid[0]


def write_audit(db, action: str, entity_id: str, summary: str) -> None:
    db.add(
        AuditLog(
            actor_user_id=None,
            actor_username="system.import",
            action=action,
            entity_type="employee",
            entity_id=entity_id,
            summary=summary,
        )
    )


def run(dry_run: bool = False) -> None:
    print("Đang đọc 7 file GenusSuite...")
    by_month = load_all_months()
    for m, tag in MONTHS:
        print(f"  Tháng {m:02d} ({tag}): {len(by_month[m])} nhân viên")

    classification = classify_employees(by_month)
    n_active = sum(1 for c in classification.values() if c["status"] == "active")
    n_resigned = sum(1 for c in classification.values() if c["status"] == "resigned")
    n_leave_note = sum(1 for c in classification.values() if c["leave_note"])
    print(f"Tổng NV xuất hiện Jan-Jul: {len(classification)}")
    print(f"  -> active (còn tính đến T7): {n_active}")
    print(f"  -> resigned (biến mất trước T7, không quay lại): {n_resigned}")
    print(f"  -> trong đó có dấu hiệu thai sản/nghỉ dài rồi quay lại: {n_leave_note}")

    if dry_run:
        print("DRY-RUN — không ghi DB.")
        return

    db = SessionLocal()
    try:
        print("Xoá dữ liệu nhân sự/lương test cũ...")
        wipe_existing_data(db)

        print("Chuẩn bị cây tổ chức thật (10 departments / 73 teams đã nạp ở 1.2)...")
        team_by_name = prepare_org_structure(db)

        print("Tạo Employee (theo bản ghi tháng gần nhất mỗi người) + ánh xạ tổ...")
        employees_by_msnv: dict[str, Employee] = {}
        unresolved_teams: list[str] = []
        for msnv, cls in classification.items():
            last_month = cls["last_month"]
            rec = by_month[last_month][msnv]
            record_date = date(2026, last_month, monthrange(2026, last_month)[1])
            team = resolve_team_for(team_by_name, rec["dept"], record_date)
            if team is None:
                unresolved_teams.append(f"MSNV {msnv} ({rec['name']}): tổ '{rec['dept']}' tháng {last_month:02d}")
            emp = Employee(
                employee_code=msnv,
                full_name=rec["name"],
                gender="M" if rec["sex"] == "Nam" else ("F" if rec["sex"] == "Nữ" else None),
                id_number=_mask_middle(rec["id_number"]),
                bank_account=_mask_middle(rec["bank_account"]),
                pay_channel="ATM",
                team_id=team.id if team else None,
                position_title=rec["position"] or None,
                join_date=rec["join_date"],
                contract_signed_at=rec["contract_signed_at"],
                probation_salary=rec["probation_salary"],
                contract_salary=rec["contract_salary"],
                status=cls["status"],
                resign_date=cls["resign_date"],
                si_enrolled=True,
                pit_enrolled=True,
            )
            db.add(emp)
            employees_by_msnv[msnv] = emp
        db.flush()

        if unresolved_teams:
            print(f"  ! {len(unresolved_teams)} nhân viên KHÔNG ánh xạ được tổ (team_id=NULL):")
            for line in unresolved_teams[:20]:
                print("    -", line)
            if len(unresolved_teams) > 20:
                print(f"    ... và {len(unresolved_teams) - 20} dòng khác.")

        print("Ghi audit log nghỉ thai sản/nghỉ dài...")
        for msnv, cls in classification.items():
            if cls["leave_note"]:
                write_audit(
                    db,
                    action="employee.import_leave_note",
                    entity_id=str(employees_by_msnv[msnv].id),
                    summary=f"MSNV {msnv} ({employees_by_msnv[msnv].full_name}): {cls['leave_note']}",
                )

        print("Tạo tài khoản Worker (MSNV / 4 số cuối CCCD hoặc MSNV, bắt đổi mật khẩu lần đầu)...")
        for msnv, emp in employees_by_msnv.items():
            db.add(
                User(
                    username=msnv,
                    full_name=emp.full_name,
                    password_hash=hash_password(default_worker_password(emp)),
                    role="worker",
                    employee_id=emp.id,
                    must_change_password=True,
                    is_active=emp.status != "resigned",
                )
            )

        print("Tạo PayPeriod + TimesheetMonth + Payslip cho 7 tháng...")
        for month_num, tag in MONTHS:
            date_from = date(2026, month_num, 1)
            date_to = date(2026, month_num, monthrange(2026, month_num)[1])
            period = PayPeriod(
                year=2026,
                month=month_num,
                date_from=date_from,
                date_to=date_to,
                official_work_days=Decimal("26"),
                salary_divisor=Decimal("26"),
                status="published",
            )
            db.add(period)
            db.flush()

            recs = by_month[month_num]
            for msnv, rec in recs.items():
                emp = employees_by_msnv.get(msnv)
                if emp is None:
                    continue
                team_this_month = resolve_team_for(team_by_name, rec["dept"], date_to)
                db.add(
                    TimesheetMonth(
                        pay_period_id=period.id,
                        employee_id=emp.id,
                        worked_days=rec["workdays_total"],
                        al_days=rec["al_days"],
                        rem_days=rec["rem_days"],
                        ot_hours_weekday=rec["ot_hours"],
                    )
                )
                confirmed_at = datetime(
                    date_to.year, date_to.month, date_to.day, 12, 0, tzinfo=timezone.utc
                )
                db.add(
                    Payslip(
                        pay_period_id=period.id,
                        employee_id=emp.id,
                        wd_salary=rec["wd_salary"],
                        allowance_total=rec["allowance_total"],
                        ot_pay=rec["ot_pay"],
                        other_adjustments=Decimal("0"),
                        gross=rec["gross"],
                        bhxh=rec["bhxh"],
                        bhyt=rec["bhyt"],
                        bhtn=rec["bhtn"],
                        union_fee=rec["union_fee"],
                        other_deductions=rec["deduct"],
                        pit_amount=Decimal("0"),
                        net=rec["net"],
                        status="confirmed",
                        confirmed_at=confirmed_at,
                        confirm_deadline=date(
                            date_to.year, date_to.month, min(date_to.day, 28)
                        ),
                        lines={
                            "source": "GenusSuite export (đã đông cứng, không qua Payroll Engine)",
                            "allowances": {
                                "attend": str(rec["allowance_attend"]),
                                "position": str(rec["allowance_position"]),
                                "toxic": str(rec["allowance_toxic"]),
                                "transport": str(rec["allowance_transport"]),
                                "pccc_hse": str(rec["allowance_pccc_hse"]),
                                "skill": str(rec["allowance_skill"]),
                                "seniority": str(rec["allowance_seniority"]),
                                "other": str(rec["allowance_other"]),
                            },
                            "ot_hours": str(rec["ot_hours"]),
                            "department_at_period": rec["dept"],
                            "team_id_at_period": str(team_this_month.id) if team_this_month else None,
                            "team_code_at_period": team_this_month.code if team_this_month else None,
                        },
                    )
                )
            print(f"  Tháng {month_num:02d}: {len(recs)} phiếu lương")

        db.commit()
        print("HOÀN TẤT nạp dữ liệu Jan-Jul/2026.")
        print(f"  Employees: {len(employees_by_msnv)}")
        print(f"  Không ánh xạ được tổ: {len(unresolved_teams)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
