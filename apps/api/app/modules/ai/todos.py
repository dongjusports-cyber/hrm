"""Thẻ việc cần làm — rule-based (5.7)."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.ai.schemas import TodoCardOut, TodosOut
from app.modules.core.models import User
from app.modules.dispute.models import Dispute
from app.modules.dispute.service import OPEN_STATUSES
from app.modules.insurance.models import InsuranceDeclaration
from app.modules.mdm.models import Employee, LabourContract
from app.modules.payroll.models import Payslip


def _can_see(user: User, module: str) -> bool:
    if user.role == "admin":
        return True
    return user.has_module(module)


def compute_todo_cards(db: Session, user: User) -> TodosOut:
    today = date.today()
    cards: list[TodoCardOut] = []

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
                    priority=10,
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
                    priority=15,
                )
            )

    cards.sort(key=lambda c: c.priority)
    return TodosOut(cards=cards, total=len(cards))
