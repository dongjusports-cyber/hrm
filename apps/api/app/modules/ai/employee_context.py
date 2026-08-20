"""Tra cứu MSNV / họ tên cho AI chat — đọc CSDL, không bịa số."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.models import AttendanceDay, PayPeriod, TimesheetMonth
from app.modules.attendance.review import count_odd_punches, list_odd_punches, odd_punch_query
from app.modules.attendance.timesheet import get_pay_period
from app.modules.attendance.annual_leave_ledger import annual_leave_snapshot_batch
from app.modules.core.models import User
from app.modules.ai.vi_labels import label_emp_status, label_pay_channel, label_payslip_status
from app.modules.mdm.models import Department, Employee, EmployeeWtRegime, Team
from app.modules.payroll.models import Payslip

_MSNV_PREFIX = re.compile(
    r"(?:msnv|mã\s*nhân\s*viên|mã\s*nv|nhân\s*viên|nv|employee)\s*[:\s#\-]*(\d{3,5})",
    re.IGNORECASE,
)
_CODE_BARE = re.compile(r"\b(\d{3,5})\b")

_OPS_NOISE = re.compile(
    r"chấm\s*lẻ|đơn\s*phép|hợp\s*đồng|bhxh|khiếu\s*nại|chuyên\s*cần|"
    r"tóm\s*tắt|hôm\s*nay|thử\s*việc|thôi\s*việc|nghỉ\s*việc|"
    r"phiếu\s*lương|bảng\s*công|chế\s*độ|việc\s*cần\s*làm",
    re.IGNORECASE,
)
_LOOKUP_LEAD = re.compile(
    r"^(?:lấy\s+)?(?:thông\s*tin|hồ\s*sơ|tra\s*cứu|tìm|xem)\s+"
    r"(?:của\s+)?(?:nhân\s*viên|nv|msnv)?\s*[:\s]*",
    re.IGNORECASE,
)
_NV_LA_AI = re.compile(
    r"(?:nhân\s*viên|nv)\s+(.+?)\s+là\s+ai\s*\??\s*$",
    re.IGNORECASE,
)

_CONTEXT_HEADER = "### Dữ liệu nhân viên (đọc từ CSDL — chỉ phân tích, không tự sửa)"


def extract_employee_codes(message: str, *, max_codes: int = 3) -> list[str]:
    """Lấy mã NV từ câu hỏi — ưu tiên sau từ khóa MSNV/NV."""
    text = (message or "").strip()
    if not text:
        return []
    found: list[str] = []
    for m in _MSNV_PREFIX.finditer(text):
        code = m.group(1)
        if code not in found:
            found.append(code)
    if not found:
        for m in _CODE_BARE.finditer(text):
            code = m.group(1)
            # Bỏ qua năm 4 chữ số bắt đầu 19/20 khi không có từ khóa MSNV
            if len(code) == 4 and code.startswith(("19", "20")):
                continue
            if code not in found:
                found.append(code)
    return found[:max_codes]


def extract_employee_name_query(message: str) -> str:
    """Họ tên sau «thông tin / hồ sơ / tra cứu / nhân viên … là ai» — không lấy câu nghiệp vụ."""
    text = (message or "").strip()
    if not text or _OPS_NOISE.search(text):
        return ""
    if extract_employee_codes(text):
        return ""
    rest = ""
    lead = _LOOKUP_LEAD.match(text)
    if lead:
        rest = text[lead.end() :].strip()
    else:
        m = _NV_LA_AI.search(text)
        if m:
            rest = m.group(1).strip()
    rest = rest.strip(" ?!.\"'«»")
    rest = re.sub(r"^(?:của\s+)", "", rest, flags=re.IGNORECASE).strip()
    rest = re.sub(r"\s+là\s+ai$", "", rest, flags=re.IGNORECASE).strip()
    if len(rest) < 2 or len(rest) > 60:
        return ""
    if rest.isdigit() or re.fullmatch(r"\d{4}-\d{2}", rest):
        return ""
    return rest


def lookup_employees_by_name(
    db: Session, name: str, *, limit: int = 5
) -> tuple[list[Employee], int]:
    q = (name or "").strip()
    if len(q) < 2:
        return [], 0
    like = f"%{q.lower()}%"
    cond = (
        Employee.deleted_at.is_(None),
        or_(
            func.lower(Employee.full_name).like(like),
            func.lower(Employee.employee_code).like(like),
        ),
    )
    total = int(db.query(func.count(Employee.id)).filter(*cond).scalar() or 0)
    rows = (
        db.query(Employee)
        .filter(*cond)
        .order_by(Employee.employee_code)
        .limit(limit)
        .all()
    )
    return rows, total


def _can_lookup_employee(user: User) -> bool:
    return user.role == "admin" or user.has_module("hr") or user.has_module("payroll")


def _fmt_money(v: Decimal | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", ".")


def _employee_lines(
    emp: Employee,
    *,
    team: Team | None,
    dept: Department | None,
    slip: tuple[Payslip, PayPeriod] | None,
    include_payroll: bool,
) -> str:
    lines = [
        f"MSNV: {emp.employee_code} | Họ tên: {emp.full_name}",
        f"Trạng thái: {label_emp_status(emp.status)} | Ngày vào: {emp.join_date or '—'} | Ngày nghỉ: {emp.resign_date or '—'}",
        f"Bộ phận: {dept.name if dept else '—'} ({dept.code if dept else '—'})",
        f"Tổ: {team.name if team else '—'} ({team.code if team else '—'})",
        f"Chức vụ: {emp.position_title or emp.position_code or '—'}",
        f"Lương HĐ: {_fmt_money(emp.contract_salary)} | Kênh lương: {label_pay_channel(emp.pay_channel)}",
        f"BHXH: {'có' if emp.si_enrolled else 'không'} | SĐT: {emp.phone or '—'}",
    ]
    if include_payroll:
        if slip:
            ps, pp = slip
            period = f"{pp.year:04d}-{pp.month:02d}"
            lines.append(
                f"Phiếu lương gần nhất ({period}): lương ngày công={ps.wd_salary}, "
                f"phụ cấp={ps.allowance_total}, lương OT={ps.ot_pay}, "
                f"tổng thu nhập={ps.gross}, thực lĩnh={ps.net}, "
                f"trạng thái={label_payslip_status(ps.status)}"
            )
        else:
            lines.append("Phiếu lương: chưa có bản ghi.")
    return "\n".join(lines)


_WT_LABEL = {
    "PREGNANT": "Đang mang thai",
    "MATERNITY": "Nghỉ thai sản",
    "CHILD": "Nuôi con nhỏ",
}


def _ops_extras_by_emp(
    db: Session,
    employees: list[Employee],
    *,
    include_payroll: bool,
) -> dict[UUID, list[str]]:
    """Phép năm, chế độ, bảng công, chấm lẻ — batch, không N+1."""
    if not employees:
        return {}
    today = datetime.now(tz=VN_TZ).date()
    ids = [e.id for e in employees]
    snaps = annual_leave_snapshot_batch(db, ids, today)
    regimes = (
        db.query(EmployeeWtRegime)
        .filter(
            EmployeeWtRegime.employee_id.in_(ids),
            EmployeeWtRegime.ended_at.is_(None),
            EmployeeWtRegime.date_from <= today,
            EmployeeWtRegime.date_to >= today,
        )
        .all()
    )
    regime_by = {r.employee_id: r for r in regimes}
    period = f"{today.year:04d}-{today.month:02d}"
    pay = get_pay_period(db, period) if include_payroll else None
    ts_by: dict[UUID, TimesheetMonth] = {}
    if pay is not None:
        ts_by = {
            row.employee_id: row
            for row in db.query(TimesheetMonth)
            .filter(
                TimesheetMonth.pay_period_id == pay.id,
                TimesheetMonth.employee_id.in_(ids),
            )
            .all()
        }
    month_start = today.replace(day=1)
    odd_rows = (
        odd_punch_query(db, month_start, today)
        .filter(AttendanceDay.employee_id.in_(ids))
        .order_by(AttendanceDay.work_date.desc())
        .limit(60)
        .all()
    )
    odd_dates: dict[UUID, list[str]] = defaultdict(list)
    for day, _emp in odd_rows:
        bucket = odd_dates[day.employee_id]
        if len(bucket) < 12:
            bucket.append(day.work_date.isoformat())

    out: dict[UUID, list[str]] = {}
    for emp in employees:
        extra: list[str] = []
        snap = snaps[emp.id]
        extra.append(
            f"Phép năm {today.year}: được hưởng={snap.entitled}, hiện tại={snap.current}, "
            f"đã dùng={snap.used}, còn lại={snap.remaining}"
        )
        regime = regime_by.get(emp.id)
        if regime:
            extra.append(
                f"Chế độ về sớm: {_WT_LABEL.get(regime.regime_type, regime.regime_type)} "
                f"{regime.hours_early}h, {regime.date_from.isoformat()} → {regime.date_to.isoformat()}"
            )
        if include_payroll:
            ts = ts_by.get(emp.id)
            if ts:
                extra.append(
                    f"Bảng công {period}: ngày công={ts.worked_days}, phép năm={ts.al_days}, "
                    f"trễ={ts.late_count}, sớm={ts.early_count}"
                )
        dates = odd_dates.get(emp.id) or []
        if dates:
            extra.append(
                f"Chấm lẻ (thiếu vào hoặc ra) từ {month_start.isoformat()} đến hôm nay: "
                f"{', '.join(dates)}. "
                "HR gọi lập biên bản rồi chấm tay đủ cặp — không bịa giờ."
            )
        else:
            extra.append("Chấm lẻ kỳ này (đến hôm nay): không có.")
        out[emp.id] = extra
    return out


def _fetch_org_maps(
    db: Session, team_ids: set[UUID]
) -> tuple[dict[UUID, Team], dict[UUID, Department]]:
    if not team_ids:
        return {}, {}
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
    dept_ids = {t.department_id for t in teams if t.department_id}
    depts = db.query(Department).filter(Department.id.in_(dept_ids)).all() if dept_ids else []
    return {t.id: t for t in teams}, {d.id: d for d in depts}


def _fetch_latest_slips(
    db: Session, emp_ids: list[UUID]
) -> dict[UUID, tuple[Payslip, PayPeriod]]:
    if not emp_ids:
        return {}
    rows = (
        db.query(Payslip, PayPeriod)
        .join(PayPeriod, PayPeriod.id == Payslip.pay_period_id)
        .filter(Payslip.employee_id.in_(emp_ids))
        .order_by(PayPeriod.year.desc(), PayPeriod.month.desc())
        .all()
    )
    out: dict[UUID, tuple[Payslip, PayPeriod]] = {}
    for ps, pp in rows:
        if ps.employee_id not in out:
            out[ps.employee_id] = (ps, pp)
    return out


def _denied_lookup() -> str:
    return (
        "### Tra cứu nhân viên\n"
        "Tài khoản không có quyền module Nhân sự/Lương — không đọc được hồ sơ từ CSDL. "
        "Liên hệ Admin cấp quyền nhân sự hoặc tính lương."
    )


def build_employee_context(db: Session, user: User, message: str) -> tuple[list[str], str]:
    """
    Trả (danh sách mã đã parse, khối ngữ cảnh).
    Chuỗi rỗng nếu không parse được mã/tên hoặc không phải câu tra cứu.
    """
    codes = extract_employee_codes(message)
    name_q = "" if codes else extract_employee_name_query(message)
    if not codes and not name_q:
        return [], ""
    if not _can_lookup_employee(user):
        return codes or [name_q], _denied_lookup()

    include_payroll = user.role == "admin" or user.has_module("payroll")
    ordered: list[Employee] = []
    missing_codes: list[str] = []
    name_total = 0

    if codes:
        employees = (
            db.query(Employee)
            .filter(Employee.employee_code.in_(codes), Employee.deleted_at.is_(None))
            .all()
        )
        by_code = {e.employee_code: e for e in employees}
        for code in codes:
            emp = by_code.get(code)
            if emp is None:
                missing_codes.append(code)
            else:
                ordered.append(emp)
    else:
        ordered, name_total = lookup_employees_by_name(db, name_q, limit=5)
        codes = [e.employee_code for e in ordered]
        if not ordered:
            return [name_q], (
                f"{_CONTEXT_HEADER}\n"
                f"Không tìm thấy nhân viên khớp «{name_q}». Thử MSNV hoặc họ tên đầy đủ."
            )

    team_ids = {e.team_id for e in ordered if e.team_id}
    teams_by_id, depts_by_id = _fetch_org_maps(db, team_ids)
    slips_by_emp = _fetch_latest_slips(db, [e.id for e in ordered]) if include_payroll else {}
    extras = _ops_extras_by_emp(db, ordered, include_payroll=include_payroll)

    blocks: list[str] = []
    if name_q and name_total > len(ordered):
        blocks.append(
            f"Có {name_total} NV khớp «{name_q}», hiện {len(ordered)}. "
            "Hỏi lại bằng MSNV để chắc một người."
        )
    elif name_q and len(ordered) > 1:
        blocks.append(
            f"Có {len(ordered)} NV khớp «{name_q}». Hỏi lại bằng MSNV nếu cần một người."
        )
    for code in missing_codes:
        blocks.append(f"MSNV {code}: không tìm thấy trong hệ thống.")
    for emp in ordered:
        team = teams_by_id.get(emp.team_id) if emp.team_id else None
        dept = depts_by_id.get(team.department_id) if team and team.department_id else None
        slip = slips_by_emp.get(emp.id)
        block = _employee_lines(
            emp,
            team=team,
            dept=dept,
            slip=slip,
            include_payroll=include_payroll,
        )
        extra = extras.get(emp.id) or []
        if extra:
            block = block + "\n" + "\n".join(extra)
        blocks.append(block)

    labels = codes if codes else [name_q]
    return labels, f"{_CONTEXT_HEADER}\n" + "\n\n".join(blocks)


def cap_note(total: int, shown: int, limit: int) -> str:
    """Ghi rõ tổng thật vs số dòng đang hiện — không để HR tưởng nhà máy chỉ có `limit` dòng."""
    if total <= 0:
        return ""
    if total <= shown:
        return f"Tổng {total} dòng."
    return (
        f"Tổng {total} dòng, hiện {shown} (tối đa {limit}). "
        "Mở trang tương ứng để xem hết — AI không bịa số."
    )


def build_punch_context(db: Session, *, limit: int = 20) -> str:
    """Danh sách chấm lẻ kỳ hiện tại — Luật 01, 0 token. Đếm đủ 400 NV, chỉ hiện `limit` dòng."""
    today = datetime.now(tz=VN_TZ).date()
    month_start = today.replace(day=1)
    total = count_odd_punches(db, month_start, today)
    rows = list_odd_punches(db, month_start, today, limit=limit)
    lines = [
        "### Chấm lẻ (thiếu vào hoặc ra) — đọc từ CSDL",
        f"Khoảng: {month_start.isoformat()} → {today.isoformat()}.",
        "Luật: ghi nhận mốc có, không bịa mốc còn lại, chưa tính công. HR gọi lập biên bản rồi chấm tay đủ cặp.",
    ]
    if total == 0:
        lines.append("Không có dòng chấm lẻ.")
        return "\n".join(lines)
    lines.append(cap_note(total, len(rows), limit))
    for day, emp in rows:
        inn = "có vào" if day.first_in else "thiếu vào"
        out = "có ra" if day.last_out else "thiếu ra"
        lines.append(f"- {emp.employee_code} {emp.full_name} {day.work_date.isoformat()} ({inn}, {out})")
    return "\n".join(lines)
