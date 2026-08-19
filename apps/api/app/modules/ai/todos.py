"""Thẻ việc cần làm — rule-based (5.7)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.ai.schemas import TodoCardOut, TodosOut
from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.models import LeaveRequest, TimesheetMonth
from app.modules.attendance.review import count_odd_punches
from app.modules.attendance.timesheet import get_pay_period
from app.modules.core.models import User
from app.modules.dispute.models import Dispute
from app.modules.dispute.service import OPEN_STATUSES
from app.modules.insurance.models import InsuranceDeclaration
from app.modules.mdm.models import Employee, EmployeeWtRegime, LabourContract
from app.modules.payroll.models import Payslip


def _can_see(user: User, module: str) -> bool:
    if user.role == "admin":
        return True
    return user.has_module(module)


def compute_todo_cards(db: Session, user: User) -> TodosOut:
    today = datetime.now(tz=VN_TZ).date()
    cards: list[TodoCardOut] = []

    if _can_see(user, "timekeeping") or _can_see(user, "hr"):
        month_start = today.replace(day=1)
        odd_n = count_odd_punches(db, month_start, today)
        if odd_n > 0:
            cards.append(
                TodoCardOut(
                    key="punch_odd_current",
                    title=f"{odd_n} ngày công chấm lẻ (thiếu vào hoặc ra)",
                    body="Không tự bịa giờ. Gọi NV lập biên bản, rồi chấm tay đủ cặp trên lưới ngày.",
                    count=odd_n,
                    target_module="timekeeping",
                    href="/m/timekeeping?view=daily",
                    ask_message="Ai chấm lẻ tháng này",
                    priority=8,
                )
            )
        pending_leave = (
            db.query(LeaveRequest).filter(LeaveRequest.status == "submitted").count()
        )
        if pending_leave > 0:
            cards.append(
                TodoCardOut(
                    key="leave_requests_pending",
                    title=f"{pending_leave} đơn phép chờ duyệt",
                    body="Công nhân gửi từ điện thoại — duyệt hoặc từ chối trên Chấm Công.",
                    count=pending_leave,
                    target_module="timekeeping",
                    href="/m/timekeeping?view=leave",
                    ask_message="Đơn phép chờ duyệt",
                    priority=9,
                )
            )

        period = f"{today.year:04d}-{today.month:02d}"
        pay = get_pay_period(db, period)
        if pay is not None:
            risk_n = (
                db.query(TimesheetMonth)
                .filter(
                    TimesheetMonth.pay_period_id == pay.id,
                    or_(TimesheetMonth.late_count >= 2, TimesheetMonth.early_count >= 2),
                )
                .count()
            )
            if risk_n > 0:
                cards.append(
                    TodoCardOut(
                        key="attendance_penalty_risk",
                        title=f"{risk_n} NV sắp phạt chuyên cần (trễ/sớm ≥ 2)",
                        body="Luật 04: trễ ≥ 2 hoặc sớm ≥ 2 còn 50%; ≥ 5 lần hoặc có vắng = 0%. Ngày chấm lẻ không đếm.",
                        count=risk_n,
                        target_module="timekeeping",
                        href="/m/timekeeping?view=monthly",
                        ask_message="Sắp mất chuyên cần",
                        priority=11,
                    )
                )

    if _can_see(user, "hr"):
        deadline = today + timedelta(days=60)
        expiring = (
            db.query(LabourContract, Employee)
            .join(Employee, Employee.id == LabourContract.employee_id)
            .filter(
                LabourContract.status == "active",
                LabourContract.end_date.isnot(None),
                LabourContract.end_date >= today,
                LabourContract.end_date <= deadline,
            )
            .count()
        )
        if expiring > 0:
            cards.append(
                TodoCardOut(
                    key="expiring_contracts_60d",
                    title=f"{expiring} hợp đồng hết hạn trong 60 ngày",
                    body="Gia hạn hoặc ký HĐ mới trước khi hết hạn.",
                    count=expiring,
                    target_module="hr",
                    href="/m/hr/contracts",
                    ask_message="Hợp đồng sắp hết hạn",
                    priority=10,
                )
            )

        expiring_wt = (
            db.query(EmployeeWtRegime)
            .join(Employee, Employee.id == EmployeeWtRegime.employee_id)
            .filter(
                EmployeeWtRegime.date_to == today + timedelta(days=3),
                EmployeeWtRegime.date_from <= today,
                EmployeeWtRegime.ended_at.is_(None),
                Employee.deleted_at.is_(None),
            )
            .count()
        )
        if expiring_wt > 0:
            cards.append(
                TodoCardOut(
                    key="wt_regime_expiring",
                    title=f"{expiring_wt} chế độ sắp hết hạn",
                    body="Chế độ đặc biệt (mang thai / nghỉ thai sản / nuôi con nhỏ) hết sau 3 ngày — gia hạn hoặc chấm dứt trên hồ sơ.",
                    count=expiring_wt,
                    target_module="hr",
                    href="/m/hr/lists/special_regime",
                    ask_message="Chế độ sắp hết hạn",
                    priority=12,
                )
            )

    if _can_see(user, "payroll") or _can_see(user, "dispute"):
        unconfirmed = (
            db.query(Payslip)
            .filter(
                Payslip.status == "published",
                Payslip.confirmed_at.is_(None),
            )
            .count()
        )
        if unconfirmed > 0:
            cards.append(
                TodoCardOut(
                    key="payslip_unconfirmed",
                    title=f"{unconfirmed} phiếu lương chưa xác nhận",
                    body="Công nhân chưa xác nhận phiếu đã phát hành.",
                    count=unconfirmed,
                    target_module="payroll",
                    href="/m/payroll",
                    ask_message="Phiếu lương chưa xác nhận",
                    priority=20,
                )
            )

    if _can_see(user, "dispute"):
        open_disputes = db.query(Dispute).filter(Dispute.status.in_(OPEN_STATUSES)).count()
        if open_disputes > 0:
            cards.append(
                TodoCardOut(
                    key="open_disputes",
                    title=f"{open_disputes} khiếu nại đang mở",
                    body="Cần xử lý hoặc phản hồi công nhân.",
                    count=open_disputes,
                    target_module="dispute",
                    href="/m/dispute",
                    ask_message="Danh sách khiếu nại đang mở",
                    priority=30,
                )
            )

    if _can_see(user, "insurance"):
        month = f"{today.year:04d}-{today.month:02d}"
        pending_bhxh = (
            db.query(InsuranceDeclaration)
            .filter(
                InsuranceDeclaration.effective_month == month,
                InsuranceDeclaration.status.in_(("draft", "exported")),
            )
            .count()
        )
        if pending_bhxh > 0:
            cards.append(
                TodoCardOut(
                    key="insurance_declarations_pending",
                    title=f"{pending_bhxh} dòng báo BHXH tháng {month} chưa nộp",
                    body="Xuất lô và đánh dấu đã nộp cơ quan BHXH.",
                    count=pending_bhxh,
                    target_module="insurance",
                    href="/m/insurance",
                    ask_message="Báo BHXH tháng này chưa nộp",
                    priority=15,
                )
            )

    cards.sort(key=lambda c: c.priority)
    return TodosOut(cards=cards, total=len(cards))
