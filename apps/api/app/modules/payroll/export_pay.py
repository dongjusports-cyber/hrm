"""Xuất bảng lương Excel — mẫu GenusSuite (TOTAL / ATM / CASH)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.core.export_log import log_export
from app.modules.core.models import User
from app.modules.payroll.export_salary_table import build_salary_table_xlsx

CHANNELS = ("ATM", "CASH", "ALL")


def build_payroll_export_xlsx(
    db: Session,
    period: str,
    channel: str,
    *,
    department_id: UUID | None = None,
    employee_code: str | None = None,
) -> tuple[bytes, int, str]:
    ch = (channel or "ALL").upper()
    if ch not in CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: channel chỉ nhận ATM, CASH hoặc ALL.",
        )
    return build_salary_table_xlsx(
        db, period, ch, department_id=department_id, employee_code=employee_code
    )


def export_payroll_channel(
    db: Session,
    user: User,
    period: str,
    channel: str,
    *,
    department_id: UUID | None = None,
    employee_code: str | None = None,
) -> tuple[bytes, str]:
    data, row_count, filename = build_payroll_export_xlsx(
        db,
        period,
        channel,
        department_id=department_id,
        employee_code=employee_code,
    )
    kind = f"payroll_{(channel or 'ALL').lower()}"
    log_export(
        db,
        user_id=user.id,
        kind=kind,
        period=period,
        row_count=row_count,
        filename=filename,
    )
    return data, filename
