"""Tra cứu MSNV cho AI chat — đọc CSDL, không bịa số."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.models import PayPeriod, TimesheetMonth
from app.modules.attendance.review import list_odd_punches
from app.modules.attendance.timesheet import get_pay_period
from app.modules.attendance.annual_leave_ledger import annual_leave_snapshot
from app.modules.core.models import User
from app.modules.ai.vi_labels import label_emp_status, label_pay_channel, label_payslip_status
from app.modules.mdm.models import Department, Employee, EmployeeWtRegime, Team
from app.modules.payroll.models import Payslip

_MSNV_PREFIX = re.compile(
    r"(?:msnv|mã\s*nhân\s*viên|mã\s*nv|nhân\s*viên|nv|employee)\s*[:\s#\-]*(\d{3,5})",
    re.IGNORECASE,
)
_CODE_BARE = re.compile(r"\b(\d{3,5})\b")

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


def _hrm_ops_lines(db: Session, emp: Employee, *, include_payroll: bool) -> list[str]:
    """Phép năm, chế độ về sớm, bảng công tháng, chấm lẻ — Luật 01/05/07."""
    today = datetime.now(tz=VN_TZ).date()
    extra: list[str] = []
    snap = annual_leave_snapshot(db, emp.id, today)
    extra.append(
        f"Phép năm {today.year}: được hưởng={snap.entitled}, hiện tại={snap.current}, "
        f"đã dùng={snap.used}, còn lại={snap.remaining}"
    )
    regime = (
        db.query(EmployeeWtRegime)
        .filter(
            EmployeeWtRegime.employee_id == emp.id,
            EmployeeWtRegime.ended_at.is_(None),
            EmployeeWtRegime.date_from <= today,
            EmployeeWtRegime.date_to >= today,
        )
        .first()
    )
    if regime:
        extra.append(
            f"Chế độ về sớm: {_WT_LABEL.get(regime.regime_type, regime.regime_type)} "
            f"{regime.hours_early}h, {regime.date_from.isoformat()} → {regime.date_to.isoformat()}"
        )
    period = f"{today.year:04d}-{today.month:02d}"
    pay = get_pay_period(db, period)
    if include_payroll and pay is not None:
        ts = (
            db.query(TimesheetMonth)
            .filter(
                TimesheetMonth.pay_period_id == pay.id,
                TimesheetMonth.employee_id == emp.id,
            )
            .one_or_none()
        )
        if ts:
            extra.append(
                f"Bảng công {period}: ngày công={ts.worked_days}, phép năm={ts.al_days}, "
                f"trễ={ts.late_count}, sớm={ts.early_count}"
            )
    month_start = today.replace(day=1)
    odd = list_odd_punches(db, month_start, today, employee_id=emp.id, limit=12)
    if odd:
        dates = ", ".join(day.work_date.isoformat() for day, _ in odd)
        extra.append(
            f"Chấm lẻ (thiếu vào hoặc ra) từ {month_start.isoformat()} đến hôm nay: {dates}. "
            "HR gọi lập biên bản rồi chấm tay đủ cặp — không bịa giờ."
        )
    else:
        extra.append("Chấm lẻ kỳ này (đến hôm nay): không có.")
    return extra


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


def build_employee_context(db: Session, user: User, message: str) -> tuple[list[str], str]:
    """
    Trả (danh sách mã đã parse, khối ngữ cảnh).
    Chuỗi rỗng nếu không parse được mã hoặc user không có quyền tra cứu.
    """
    codes = extract_employee_codes(message)
    if not codes:
        return [], ""
    if not _can_lookup_employee(user):
        return codes, (
            "### Tra cứu nhân viên\n"
            "Tài khoản không có quyền module Nhân sự/Lương — không đọc được hồ sơ từ CSDL. "
            "Liên hệ Admin cấp quyền nhân sự hoặc tính lương."
        )

    include_payroll = user.role == "admin" or user.has_module("payroll")
    employees = (
        db.query(Employee).filter(Employee.employee_code.in_(codes)).all()
    )
    by_code = {e.employee_code: e for e in employees}
    team_ids = {e.team_id for e in employees if e.team_id}
    teams_by_id, depts_by_id = _fetch_org_maps(db, team_ids)
    slips_by_emp = _fetch_latest_slips(db, [e.id for e in employees]) if include_payroll else {}

    blocks: list[str] = []
    for code in codes:
        emp = by_code.get(code)
        if emp is None:
            blocks.append(f"MSNV {code}: không tìm thấy trong hệ thống.")
            continue
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
        extra = _hrm_ops_lines(db, emp, include_payroll=include_payroll)
        if extra:
            block = block + "\n" + "\n".join(extra)
        blocks.append(block)

    return codes, f"{_CONTEXT_HEADER}\n" + "\n\n".join(blocks)


def build_punch_context(db: Session, *, limit: int = 20) -> str:
    """Danh sách chấm lẻ kỳ hiện tại — Luật 01, 0 token."""
    today = datetime.now(tz=VN_TZ).date()
    month_start = today.replace(day=1)
    rows = list_odd_punches(db, month_start, today, limit=limit)
    n = len(rows)
    lines = [
        "### Chấm lẻ (thiếu vào hoặc ra) — đọc từ CSDL",
        f"Khoảng: {month_start.isoformat()} → {today.isoformat()}.",
        "Luật: ghi nhận mốc có, không bịa mốc còn lại, chưa tính công. HR gọi lập biên bản rồi chấm tay đủ cặp.",
    ]
    if n == 0:
        lines.append("Không có dòng chấm lẻ.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {n}")
    for day, emp in rows:
        inn = "có vào" if day.first_in else "thiếu vào"
        out = "có ra" if day.last_out else "thiếu ra"
        lines.append(f"- {emp.employee_code} {emp.full_name} {day.work_date.isoformat()} ({inn}, {out})")
    return "\n".join(lines)
