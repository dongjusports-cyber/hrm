"""Luồng HĐ lao động GenusSuite — TV → HD1 → HD2 → VTH, TIMES/seq_no."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.mdm.models import Employee, LabourContract

CONTRACT_TYPE_LABELS: dict[str, str] = {
    "TV": "Thử việc (TV)",
    "HD1": "HĐ 1 năm — lần 1 (HD1)",
    "HD2": "HĐ 1 năm — lần 2 (HD2)",
    "VTH": "Vô thời hạn (VTH)",
}

NEXT_TYPES: dict[str, list[str]] = {
    "TV": ["HD1"],
    "HD1": ["HD2", "VTH"],
    "HD2": ["VTH"],
    "VTH": [],
}


def contract_type_label(code: str | None) -> str:
    if not code:
        return "—"
    return CONTRACT_TYPE_LABELS.get(code.upper(), code.upper())


def format_contract_no(employee_code: str, contract_type_code: str) -> str:
    code = contract_type_code.upper()
    display = code
    if code == "HD1":
        display = "HĐ1"
    elif code == "HD2":
        display = "HĐ2"
    return f"{employee_code}/{display}"


def times_label(seq_no: int, contract_type_code: str) -> str:
    code = contract_type_code.upper()
    if code == "TV":
        return "Thử việc"
    if code == "VTH":
        return f"Lần {seq_no} · VTH"
    if code == "HD1":
        return f"Lần {seq_no} · HĐ lần 1"
    if code == "HD2":
        return f"Lần {seq_no} · HĐ lần 2"
    return f"Lần {seq_no} · {code}"


def _month_add(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def contract_end_date(start: date, contract_type_code: str) -> date | None:
    code = contract_type_code.upper()
    if code in ("HD1", "HD2"):
        return _month_add(start, 12) - timedelta(days=1)
    if code == "TV":
        return _month_add(start, 1) - timedelta(days=1)
    if code == "VTH":
        return None
    return _month_add(start, 12) - timedelta(days=1)


def default_next_type(previous: str | None, *, emp_status: str) -> str:
    if previous:
        nxt = NEXT_TYPES.get(previous.upper(), [])
        if nxt:
            return nxt[0]
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: nhân viên đã có HĐ vô thời hạn — không ký tiếp được.",
        )
    if emp_status == "probation":
        return "TV"
    return "HD1"


def infer_current_contract_type(emp: Employee) -> str:
    """Suy loại HĐ hiện tại khi nạp bootstrap (không có lịch sử GenusSuite)."""
    if emp.status == "probation":
        return "TV"
    # NV đã chính thức / thai sản — giả định đang ở VTH (tránh cảnh báo hết hạn sai).
    return "VTH"


def allowed_first_contract_types(emp_status: str, suggested: str) -> list[str]:
    """Loại HĐ được chọn lần đầu — thử việc auto TV; sếp có thể chỉ định khác."""
    if emp_status == "probation":
        return ["TV", "HD1"]
    if emp_status == "active":
        return ["HD1", "HD2", "VTH"]
    return [suggested]


def get_latest_contract(db: Session, employee_id: UUID) -> LabourContract | None:
    return (
        db.query(LabourContract)
        .filter(LabourContract.employee_id == employee_id)
        .order_by(LabourContract.seq_no.desc(), LabourContract.start_date.desc())
        .first()
    )


def get_active_contract(db: Session, employee_id: UUID) -> LabourContract | None:
    return (
        db.query(LabourContract)
        .filter(
            LabourContract.employee_id == employee_id,
            LabourContract.status == "active",
        )
        .order_by(LabourContract.start_date.desc())
        .first()
    )


def next_seq_no(db: Session, employee_id: UUID) -> int:
    from sqlalchemy import func

    max_seq = (
        db.query(func.max(LabourContract.seq_no))
        .filter(LabourContract.employee_id == employee_id)
        .scalar()
    )
    return int(max_seq or 0) + 1


def suggest_start_date(
    previous: LabourContract | None,
    *,
    emp: Employee,
    contract_type_code: str,
) -> date:
    today = date.today()
    if previous and previous.end_date:
        return previous.end_date + timedelta(days=1)
    if emp.join_date and contract_type_code.upper() == "TV":
        return emp.join_date
    return today


def build_renew_preview(db: Session, emp: Employee) -> dict:
    previous = get_latest_contract(db, emp.id)
    prev_type = previous.contract_type_code.upper() if previous else None

    if prev_type == "VTH":
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: NV đã có HĐ vô thời hạn — không cần ký tiếp.",
        )

    if prev_type:
        allowed = NEXT_TYPES.get(prev_type, [])
        if not allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Trợ Lý AI: không có bước ký tiếp sau {prev_type}.",
            )
        suggested_type = allowed[0]
    else:
        suggested_type = default_next_type(None, emp_status=emp.status)
        allowed = allowed_first_contract_types(emp.status, suggested_type)

    start = suggest_start_date(previous, emp=emp, contract_type_code=suggested_type)
    end = contract_end_date(start, suggested_type)
    seq = next_seq_no(db, emp.id)
    base = previous.base_salary if previous else emp.contract_salary

    prev_label = contract_type_label(prev_type) if prev_type else None
    msg = (
        f"Ký tiếp: {contract_type_label(suggested_type)} (lần {seq})"
        + (f" — sau {prev_label}" if prev_label else " — HĐ đầu tiên")
        + f". Bắt đầu {start.strftime('%d/%m/%Y')}."
    )
    if end:
        msg += f" Hết {end.strftime('%d/%m/%Y')}."
    else:
        msg += " VTH — không có ngày hết."

    return {
        "employee_id": emp.id,
        "employee_code": emp.employee_code,
        "previous_contract_id": previous.id if previous else None,
        "previous_contract_type_code": prev_type,
        "previous_contract_type_label": prev_label,
        "suggested_contract_type_code": suggested_type,
        "suggested_contract_type_label": contract_type_label(suggested_type),
        "suggested_seq_no": seq,
        "suggested_contract_no": format_contract_no(emp.employee_code, suggested_type),
        "suggested_start_date": start,
        "suggested_end_date": end,
        "suggested_sign_date": date.today(),
        "suggested_base_salary": base,
        "allowed_contract_type_codes": allowed,
        "message": msg,
    }


def expire_superseded(db: Session, employee_id: UUID, new_start: date) -> None:
    for row in (
        db.query(LabourContract)
        .filter(
            LabourContract.employee_id == employee_id,
            LabourContract.status == "active",
        )
        .all()
    ):
        if row.end_date and row.end_date < new_start:
            row.status = "expired"


def sync_employee_after_contract(emp: Employee, contract_type_code: str) -> None:
    code = contract_type_code.upper()
    if code == "TV":
        emp.status = "probation"
    elif code in ("HD1", "HD2", "VTH") and emp.status in ("probation", "active"):
        emp.status = "active"


def bootstrap_first_contract(
    db: Session,
    emp: Employee,
    *,
    sign_date: date | None = None,
) -> LabourContract | None:
    """Tạo HĐ đầu tiên khi tạo NV mới — TV nếu thử việc, không ghi đè nếu đã có."""
    if get_latest_contract(db, emp.id) is not None:
        return None
    ctype = infer_current_contract_type(emp)
    start = emp.join_date or date.today()
    sign = sign_date or emp.contract_signed_at or start
    if ctype == "TV":
        end = contract_end_date(start, "TV")
        salary = emp.probation_salary or emp.contract_salary
    else:
        end = None
        salary = emp.contract_salary
    row = LabourContract(
        employee_id=emp.id,
        contract_type_code=ctype,
        seq_no=1,
        sign_date=sign,
        start_date=start,
        end_date=end,
        base_salary=salary or Decimal("0"),
        position_code=emp.position_code,
        team_id=emp.team_id,
        status="active",
    )
    db.add(row)
    return row
