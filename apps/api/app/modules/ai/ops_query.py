"""Lớp B — ngữ cảnh nghiệp vụ nhà máy (0 token khi không cần phân tích)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.ai.employee_context import build_punch_context
from app.modules.ai.fast_reply import detect_ops_kind
from app.modules.ai.vi_labels import label_dispute_status, label_period_status
from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.models import LeaveRequest, PayPeriod, TimesheetMonth
from app.modules.attendance.timesheet import get_pay_period
from app.modules.core.models import User
from app.modules.dispute.models import Dispute
from app.modules.dispute.service import OPEN_STATUSES, user_can_view_disputes
from app.modules.insurance.models import InsuranceDeclaration
from app.modules.mdm.models import Employee, EmployeeWtRegime, LabourContract
from app.modules.payroll.models import Payslip

OPS_DIRECT_KINDS = frozenset(
    {
        "employee_lookup",
        "punch_review",
        "leave_review",
        "contract_review",
        "insurance_review",
        "payroll_review",
        "dispute_list",
        "wt_review",
        "attendance_risk",
        "daily_briefing",
    }
)

_WT_LABEL = {
    "PREGNANT": "Đang mang thai",
    "MATERNITY": "Nghỉ thai sản",
    "CHILD": "Nuôi con nhỏ",
}

_INS_TYPE = {
    "increase": "tăng",
    "decrease": "giảm",
    "salary_change": "đổi lương",
}


def _can_see(user: User, module: str) -> bool:
    if user.role == "admin":
        return True
    return user.has_module(module)


def _denied(header: str) -> str:
    return (
        f"{header}\n"
        "Tài khoản không có quyền module tương ứng — không đọc được số liệu từ CSDL. "
        "Liên hệ Admin."
    )


def build_leave_context(db: Session, *, limit: int = 20) -> str:
    rows = (
        db.query(LeaveRequest, Employee)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .filter(LeaveRequest.status == "submitted")
        .order_by(LeaveRequest.submitted_at.desc().nullslast(), LeaveRequest.from_date)
        .limit(limit)
        .all()
    )
    lines = [
        "### Đơn phép chờ duyệt — đọc từ CSDL",
        "Luật 05: HR duyệt/từ chối trên Chấm Công. AI không tự duyệt.",
    ]
    if not rows:
        lines.append("Không có đơn status=submitted.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {len(rows)}")
    for req, emp in rows:
        half = ""
        if req.from_half or req.to_half:
            half = " (nửa ngày)"
        lines.append(
            f"- {emp.employee_code} {emp.full_name}: {req.leave_type_code} "
            f"{req.from_date.isoformat()} → {req.to_date.isoformat()} "
            f"({req.total_days} ngày){half}"
        )
    return "\n".join(lines)


def build_contract_context(db: Session, *, limit: int = 20) -> str:
    today = datetime.now(tz=VN_TZ).date()
    deadline = today + timedelta(days=60)
    rows = (
        db.query(LabourContract, Employee)
        .join(Employee, Employee.id == LabourContract.employee_id)
        .filter(
            LabourContract.status == "active",
            LabourContract.end_date.isnot(None),
            LabourContract.end_date >= today,
            LabourContract.end_date <= deadline,
        )
        .order_by(LabourContract.end_date, Employee.employee_code)
        .limit(limit)
        .all()
    )
    lines = [
        "### Hợp đồng hết hạn trong 60 ngày — đọc từ CSDL",
        f"Mốc hôm nay (VN): {today.isoformat()}. Gia hạn hoặc ký HĐ mới trước ngày hết.",
    ]
    if not rows:
        lines.append("Không có HĐ active hết hạn trong 60 ngày.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {len(rows)}")
    for c, emp in rows:
        lines.append(
            f"- {emp.employee_code} {emp.full_name}: {c.contract_type_code} "
            f"hết {c.end_date.isoformat()}"
        )
    return "\n".join(lines)


def build_insurance_context(db: Session, *, limit: int = 20) -> str:
    today = datetime.now(tz=VN_TZ).date()
    month = f"{today.year:04d}-{today.month:02d}"
    rows = (
        db.query(InsuranceDeclaration, Employee)
        .join(Employee, Employee.id == InsuranceDeclaration.employee_id)
        .filter(
            InsuranceDeclaration.effective_month == month,
            InsuranceDeclaration.status.in_(("draft", "exported")),
        )
        .order_by(Employee.employee_code)
        .limit(limit)
        .all()
    )
    lines = [
        "### Báo BHXH tháng chưa nộp — đọc từ CSDL",
        f"Tháng {month}. Luật 06: xuất lô rồi đánh dấu đã nộp cơ quan BHXH. AI không nộp hộ.",
    ]
    if not rows:
        lines.append("Không có dòng draft/exported tháng này.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {len(rows)}")
    for row, emp in rows:
        kind = _INS_TYPE.get(row.declaration_type, row.declaration_type)
        lines.append(
            f"- {emp.employee_code} {emp.full_name}: {kind}, trạng thái={row.status}"
        )
    return "\n".join(lines)


def build_payroll_ops_context(db: Session) -> str:
    today = datetime.now(tz=VN_TZ).date()
    unconfirmed = (
        db.query(Payslip)
        .filter(Payslip.status == "published", Payslip.confirmed_at.is_(None))
        .count()
    )
    lines = [
        "### Phiếu lương / khóa kỳ — đọc từ CSDL",
        f"Hôm nay (VN): {today.isoformat()}. Luật 03: trả lương ngày 08 tháng sau.",
        f"Phiếu đã phát hành chưa xác nhận: {unconfirmed}.",
    ]
    periods = (
        db.query(PayPeriod)
        .filter(PayPeriod.status.in_(["open", "calculating", "published"]))
        .order_by(PayPeriod.year, PayPeriod.month)
        .all()
    )
    overdue: list[str] = []
    for pay in periods:
        if pay.month == 12:
            pay_year, pay_month = pay.year + 1, 1
        else:
            pay_year, pay_month = pay.year, pay.month + 1
        payday = datetime(pay_year, pay_month, 8).date()
        period = f"{pay.year:04d}-{pay.month:02d}"
        if today > payday:
            overdue.append(
                f"{period} ({label_period_status(pay.status)}, hạn trả {payday.isoformat()})"
            )
    if overdue:
        lines.append("Kỳ chưa khóa sau ngày trả lương: " + "; ".join(overdue[:12]))
    else:
        lines.append("Không có kỳ quá hạn khóa (sau ngày 08).")
    return "\n".join(lines)


def build_dispute_list_context(db: Session, *, limit: int = 20) -> str:
    rows = (
        db.query(Dispute, Employee)
        .join(Employee, Employee.id == Dispute.employee_id)
        .filter(Dispute.status.in_(OPEN_STATUSES))
        .order_by(Dispute.created_at.desc())
        .limit(limit)
        .all()
    )
    lines = [
        "### Khiếu nại đang mở — đọc từ CSDL",
        "AI chỉ đọc và đề xuất. Không tự đóng/xác nhận khiếu nại.",
    ]
    if not rows:
        lines.append("Không có khiếu nại open/ai_reviewed/hr_pending.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {len(rows)}")
    for d, emp in rows:
        lines.append(
            f"- {d.code} {emp.employee_code} {emp.full_name}: "
            f"{label_dispute_status(d.status)} / {d.reason_code}"
        )
    return "\n".join(lines)


def build_wt_context(db: Session, *, limit: int = 20) -> str:
    today = datetime.now(tz=VN_TZ).date()
    target = today + timedelta(days=3)
    rows = (
        db.query(EmployeeWtRegime, Employee)
        .join(Employee, Employee.id == EmployeeWtRegime.employee_id)
        .filter(
            EmployeeWtRegime.date_to == target,
            EmployeeWtRegime.date_from <= today,
            EmployeeWtRegime.ended_at.is_(None),
            Employee.deleted_at.is_(None),
        )
        .order_by(Employee.employee_code)
        .limit(limit)
        .all()
    )
    lines = [
        "### Chế độ về sớm hết hạn T−3 — đọc từ CSDL",
        f"Luật 07: nhắc 3 ngày trước date_to. Mốc hết = {target.isoformat()}.",
    ]
    if not rows:
        lines.append("Không có chế độ hết đúng sau 3 ngày.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {len(rows)}")
    for regime, emp in rows:
        label = _WT_LABEL.get(regime.regime_type, regime.regime_type)
        lines.append(
            f"- {emp.employee_code} {emp.full_name}: {label} "
            f"{regime.hours_early}h, hết {regime.date_to.isoformat()}"
        )
    return "\n".join(lines)


def build_attendance_risk_context(db: Session, *, limit: int = 20) -> str:
    today = datetime.now(tz=VN_TZ).date()
    period = f"{today.year:04d}-{today.month:02d}"
    pay = get_pay_period(db, period)
    lines = [
        "### Nguy cơ chuyên cần kỳ hiện tại — đọc từ CSDL",
        "Luật 04: trễ ≥ 2 hoặc sớm ≥ 2 → 50%; ≥ 5 lần hoặc có vắng → 0%. Đếm riêng, ngày chấm lẻ không tính.",
        f"Kỳ {period}.",
    ]
    if pay is None:
        lines.append("Chưa có kỳ lương tháng này — chưa có bảng công để đếm trễ/sớm.")
        return "\n".join(lines)
    rows = (
        db.query(TimesheetMonth, Employee)
        .join(Employee, Employee.id == TimesheetMonth.employee_id)
        .filter(
            TimesheetMonth.pay_period_id == pay.id,
            or_(TimesheetMonth.late_count >= 2, TimesheetMonth.early_count >= 2),
        )
        .order_by(TimesheetMonth.late_count.desc(), TimesheetMonth.early_count.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        lines.append("Không có NV trễ ≥ 2 hoặc sớm ≥ 2 trên bảng công kỳ này.")
        return "\n".join(lines)
    lines.append(f"Số dòng (tối đa {limit} hiện): {len(rows)}")
    for ts, emp in rows:
        lines.append(
            f"- {emp.employee_code} {emp.full_name}: trễ={ts.late_count}, sớm={ts.early_count}"
        )
    return "\n".join(lines)


def build_briefing_context(db: Session, user: User) -> str:
    from app.modules.ai.todos import compute_todo_cards

    today = datetime.now(tz=VN_TZ).date()
    todos = compute_todo_cards(db, user)
    lines = [
        "### Việc cần làm hôm nay — đọc từ CSDL",
        f"Ngày VN: {today.isoformat()}. AI chỉ đọc — không tự sửa công/lương/phép.",
    ]
    if todos.total == 0:
        lines.append("Không có thẻ việc tồn. Kiểm tra Chấm Công nếu vừa đồng bộ máy chấm.")
        return "\n".join(lines)
    lines.append(f"Số việc: {todos.total}. Làm theo thứ tự ưu tiên (số nhỏ = gấp).")
    for card in todos.cards:
        lines.append(f"- [{card.priority}] {card.title}: {card.body}")
    return "\n".join(lines)


def resolve_ops_query(db: Session, user: User, message: str) -> tuple[str, str]:
    """(kind, khối ngữ cảnh) — chuỗi rỗng nếu không phải câu nghiệp vụ nhà máy."""
    kind = detect_ops_kind(message)
    if not kind:
        return "", ""

    need = {
        "punch_review": ("timekeeping", "hr"),
        "leave_review": ("timekeeping", "hr"),
        "attendance_risk": ("timekeeping", "hr", "payroll"),
        "contract_review": ("hr",),
        "wt_review": ("hr",),
        "insurance_review": ("insurance",),
        "payroll_review": ("payroll", "dispute"),
        "dispute_list": (),
        "daily_briefing": (),
    }[kind]

    if kind == "dispute_list":
        allowed = user_can_view_disputes(user)
    elif kind == "daily_briefing":
        allowed = True
    else:
        allowed = user.role == "admin" or any(_can_see(user, m) for m in need)

    headers = {
        "punch_review": "### Chấm lẻ (thiếu vào hoặc ra) — đọc từ CSDL",
        "leave_review": "### Đơn phép chờ duyệt — đọc từ CSDL",
        "contract_review": "### Hợp đồng hết hạn trong 60 ngày — đọc từ CSDL",
        "insurance_review": "### Báo BHXH tháng chưa nộp — đọc từ CSDL",
        "payroll_review": "### Phiếu lương / khóa kỳ — đọc từ CSDL",
        "dispute_list": "### Khiếu nại đang mở — đọc từ CSDL",
        "wt_review": "### Chế độ về sớm hết hạn T−3 — đọc từ CSDL",
        "attendance_risk": "### Nguy cơ chuyên cần kỳ hiện tại — đọc từ CSDL",
        "daily_briefing": "### Việc cần làm hôm nay — đọc từ CSDL",
    }
    if not allowed:
        return kind, _denied(headers[kind])

    builders = {
        "punch_review": lambda: build_punch_context(db),
        "leave_review": lambda: build_leave_context(db),
        "contract_review": lambda: build_contract_context(db),
        "insurance_review": lambda: build_insurance_context(db),
        "payroll_review": lambda: build_payroll_ops_context(db),
        "dispute_list": lambda: build_dispute_list_context(db),
        "wt_review": lambda: build_wt_context(db),
        "attendance_risk": lambda: build_attendance_risk_context(db),
        "daily_briefing": lambda: build_briefing_context(db, user),
    }
    return kind, builders[kind]()
