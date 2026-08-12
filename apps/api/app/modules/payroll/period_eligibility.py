"""NV có thuộc kỳ lương hay không — dùng chung Payroll / Export / KPI."""

from __future__ import annotations

from datetime import date

from app.modules.mdm.models import Employee


def employee_on_payroll_period(
    emp: Employee,
    period_from: date,
    period_to: date,
) -> bool:
    """NV thuộc kỳ: đã vào trước/trong kỳ và chưa nghỉ trước ngày đầu kỳ.

    - Nghỉ giữa tháng (resign_date trong kỳ) → vẫn tính (lương đến ngày nghỉ).
    - Đã nghỉ trước kỳ → loại khỏi bảng lương (kể cả tái tuyển rồi nghỉ lại).
    """
    if emp.deleted_at is not None:
        return False
    if emp.join_date and emp.join_date > period_to:
        return False
    if emp.status == "resigned":
        if emp.resign_date is None:
            return False
        if emp.resign_date < period_from:
            return False
    elif emp.resign_date is not None and emp.resign_date < period_from:
        return False
    return True
