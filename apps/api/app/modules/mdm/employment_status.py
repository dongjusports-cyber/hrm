"""Trạng thái làm việc suy ra — thử việc / thai sản / chính thức (03§, 10§, 22§)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.attendance.models import LeaveRequest
from app.modules.mdm.models import Employee

MATERNITY_LEAVE_CODES = frozenset({"MLE", "MC"})
PROBATION_CONTRACT_CODE = "TV"

STATUS_LABELS: dict[str, str] = {
    "active": "Chính thức",
    "probation": "Thử việc",
    "maternity": "Thai sản",
    "resigned": "Đã nghỉ",
    "suspended": "Tạm ngưng",
}


def maternity_employee_ids(db: Session, as_of: date | None = None) -> set[UUID]:
    """NV đang nghỉ thai sản (đơn approved bao phủ ngày as_of)."""
    today = as_of or date.today()
    rows = (
        db.query(LeaveRequest.employee_id)
        .filter(
            LeaveRequest.leave_type_code.in_(MATERNITY_LEAVE_CODES),
            LeaveRequest.status == "approved",
            LeaveRequest.from_date <= today,
            LeaveRequest.to_date >= today,
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def effective_employment_status(
    emp: Employee,
    *,
    active_contract_type: str | None = None,
    on_maternity_leave: bool = False,
    as_of: date | None = None,
) -> str:
    """Suy ra trạng thái hiển thị — ưu tiên: resigned > maternity > probation > suspended > active."""
    today = as_of or date.today()
    if emp.status == "resigned":
        return "resigned"
    if emp.status == "maternity" or on_maternity_leave:
        return "maternity"
    if emp.status == "probation":
        return "probation"
    if emp.status == "suspended":
        return "suspended"
    if active_contract_type == PROBATION_CONTRACT_CODE:
        return "probation"
    if emp.contract_signed_at is None or emp.contract_signed_at > today:
        return "probation"
    return "active"


def status_label(code: str) -> str:
    return STATUS_LABELS.get(code, code)
