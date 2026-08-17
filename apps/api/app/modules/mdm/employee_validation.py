"""Kiểm tra dữ liệu NV — một nguồn rule cho API validate + create/update (P0)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.mdm.models import Employee, Team
from app.modules.mdm.schemas import EmployeeCreate, EmployeeUpdate

ValidationLevel = Literal["error", "warn", "info"]
MSNV_RE = re.compile(r"^\d{3,6}$")
CCCD_RE = re.compile(r"^\d{12}$")
MAX_SALARY = Decimal("500000000")
MSNV_GAP_WARN = 50


@dataclass
class ValidationIssue:
    field: str
    code: str
    level: ValidationLevel
    message: str
    meta: dict | None = None


def _issues_to_dict(items: list[ValidationIssue]) -> list[dict]:
    return [
        {
            "field": i.field,
            "code": i.code,
            "level": i.level,
            "message": i.message,
            "meta": i.meta,
        }
        for i in items
    ]


def raise_on_errors(issues: list[ValidationIssue]) -> None:
    errors = [i for i in issues if i.level == "error"]
    if not errors:
        return
    first = errors[0]
    raise HTTPException(status_code=400, detail=first.message)


def suggest_employee_code(db: Session) -> str:
    """Gợi ý MSNV tiếp theo — max số hiện có + 1."""
    rows = (
        db.query(Employee.employee_code)
        .filter(Employee.deleted_at.is_(None))
        .all()
    )
    max_num = 0
    for (code,) in rows:
        text = (code or "").strip()
        if text.isdigit():
            max_num = max(max_num, int(text))
    return str(max_num + 1 if max_num > 0 else 1000)


def _parse_money(raw: Decimal | str | None) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw).replace(",", "").replace(" ", ""))
    except (InvalidOperation, ValueError):
        return None


def _name_word_count(name: str) -> int:
    return len([p for p in name.strip().split() if p])


def _find_id_number_owner(db: Session, id_number: str, exclude_id: UUID | None) -> Employee | None:
    q = db.query(Employee).filter(
        Employee.deleted_at.is_(None),
        Employee.id_number == id_number,
    )
    if exclude_id is not None:
        q = q.filter(Employee.id != exclude_id)
    return q.first()


def _validate_common_fields(
    db: Session,
    *,
    employee_code: str | None,
    full_name: str | None,
    contract_salary: Decimal | str | None,
    probation_salary: Decimal | str | None = None,
    pay_channel: str | None = None,
    bank_account: str | None = None,
    status: str | None = None,
    join_date: date | None = None,
    resign_date: date | None = None,
    id_number: str | None = None,
    team_id: UUID | None = None,
    exclude_emp_id: UUID | None = None,
    require_code: bool,
    require_name: bool,
    require_salary: bool,
    require_team: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if require_code and employee_code is not None:
        code = employee_code.strip()
        if not code:
            issues.append(
                ValidationIssue("employee_code", "required", "error", "Trợ Lý AI: MSNV không được để trống.")
            )
        elif not MSNV_RE.match(code):
            issues.append(
                ValidationIssue(
                    "employee_code",
                    "format",
                    "error",
                    "Trợ Lý AI: MSNV chỉ gồm 3–6 chữ số.",
                )
            )
        else:
            clash = (
                db.query(Employee)
                .filter(
                    Employee.deleted_at.is_(None),
                    Employee.employee_code == code,
                )
                .first()
            )
            if clash is not None and (exclude_emp_id is None or clash.id != exclude_emp_id):
                issues.append(
                    ValidationIssue(
                        "employee_code",
                        "duplicate",
                        "error",
                        f"Trợ Lý AI: MSNV '{code}' đã tồn tại.",
                    )
                )
            else:
                try:
                    num = int(code)
                    suggested = int(suggest_employee_code(db))
                    if abs(num - suggested) > MSNV_GAP_WARN:
                        issues.append(
                            ValidationIssue(
                                "employee_code",
                                "gap",
                                "warn",
                                f"Trợ Lý AI: MSNV {code} lệch xa dãy gợi ý ({suggested}). Kiểm tra có nhầm số không?",
                                meta={"suggested": str(suggested)},
                            )
                        )
                except ValueError:
                    pass

    if require_name and full_name is not None:
        name = full_name.strip()
        if not name:
            issues.append(
                ValidationIssue("full_name", "required", "error", "Trợ Lý AI: Họ tên không được để trống.")
            )
        elif _name_word_count(name) < 2:
            issues.append(
                ValidationIssue(
                    "full_name",
                    "format",
                    "error",
                    "Trợ Lý AI: Họ tên cần ít nhất 2 từ (Họ + Tên).",
                )
            )

    if require_salary and contract_salary is not None:
        sal = _parse_money(contract_salary)
        if sal is None:
            issues.append(
                ValidationIssue(
                    "contract_salary",
                    "format",
                    "error",
                    "Trợ Lý AI: Lương HĐ không hợp lệ.",
                )
            )
        elif sal <= 0:
            issues.append(
                ValidationIssue(
                    "contract_salary",
                    "min",
                    "error",
                    "Trợ Lý AI: Lương HĐ phải lớn hơn 0.",
                )
            )
        elif sal > MAX_SALARY:
            issues.append(
                ValidationIssue(
                    "contract_salary",
                    "max",
                    "error",
                    "Trợ Lý AI: Lương HĐ vượt mức cho phép.",
                )
            )

    if probation_salary is not None and str(probation_salary).strip() not in ("", "0", "0.0"):
        prob = _parse_money(probation_salary)
        sal = _parse_money(contract_salary) if contract_salary is not None else None
        if prob is not None and sal is not None and prob > 0 and sal > 0 and prob > sal:
            issues.append(
                ValidationIssue(
                    "probation_salary",
                    "gt_contract",
                    "error",
                    "Trợ Lý AI: Lương thử việc không được cao hơn lương HĐ.",
                )
            )

    if pay_channel is not None:
        up = pay_channel.upper()
        if up not in ("ATM", "CASH"):
            issues.append(
                ValidationIssue(
                    "pay_channel",
                    "enum",
                    "error",
                    "Trợ Lý AI: Kênh lương chỉ ATM hoặc CASH.",
                )
            )
        elif up == "ATM" and not (bank_account or "").strip():
            issues.append(
                ValidationIssue(
                    "bank_account",
                    "atm_no_account",
                    "warn",
                    "Trợ Lý AI: Kênh ATM nhưng chưa có STK — nên chọn CASH hoặc bổ sung STK trước kỳ lương.",
                )
            )

    if status is not None:
        allowed = {"active", "probation", "resigned", "suspended", "maternity"}
        if status not in allowed:
            issues.append(
                ValidationIssue("status", "enum", "error", "Trợ Lý AI: Trạng thái không hợp lệ.")
            )
        if status == "probation" and join_date is None:
            issues.append(
                ValidationIssue(
                    "join_date",
                    "required_probation",
                    "error",
                    "Trợ Lý AI: NV thử việc cần ngày vào.",
                )
            )

    today = date.today()
    if join_date is not None and join_date > today + timedelta(days=30):
        issues.append(
            ValidationIssue(
                "join_date",
                "future",
                "error",
                "Trợ Lý AI: Ngày vào không được quá 30 ngày so với hôm nay.",
            )
        )

    if join_date is not None and resign_date is not None and resign_date < join_date:
        issues.append(
            ValidationIssue(
                "resign_date",
                "before_join",
                "error",
                "Trợ Lý AI: Ngày nghỉ không được trước ngày vào.",
            )
        )

    if id_number is not None and str(id_number).strip():
        cccd = str(id_number).strip()
        if not CCCD_RE.match(cccd):
            issues.append(
                ValidationIssue(
                    "id_number",
                    "format",
                    "error",
                    "Trợ Lý AI: CCCD phải đúng 12 chữ số.",
                )
            )
        else:
            owner = _find_id_number_owner(db, cccd, exclude_emp_id)
            if owner is not None:
                if owner.status == "resigned":
                    issues.append(
                        ValidationIssue(
                            "id_number",
                            "duplicate_resigned",
                            "error",
                            f"Trợ Lý AI: CCCD trùng NV đã nghỉ MSNV {owner.employee_code} "
                            f"({owner.full_name}). Dùng «Tái tuyển», không tạo NV mới.",
                            meta={
                                "employee_id": str(owner.id),
                                "employee_code": owner.employee_code,
                                "full_name": owner.full_name,
                                "action": "rehire",
                            },
                        )
                    )
                else:
                    issues.append(
                        ValidationIssue(
                            "id_number",
                            "duplicate",
                            "error",
                            f"Trợ Lý AI: CCCD trùng MSNV {owner.employee_code} ({owner.full_name}).",
                            meta={
                                "employee_code": owner.employee_code,
                                "full_name": owner.full_name,
                            },
                        )
                    )

    if require_team and team_id is None:
        issues.append(
            ValidationIssue(
                "team_id",
                "required",
                "error",
                "Trợ Lý AI: cần chọn Tổ cho nhân viên — mọi NV phải thuộc về một tổ (23§).",
            )
        )
    elif team_id is not None:
        team = db.get(Team, team_id)
        if team is None:
            issues.append(
                ValidationIssue("team_id", "not_found", "error", "Trợ Lý AI: Tổ không tồn tại.")
            )
        else:
            today = date.today()
            if team.effective_to is not None and team.effective_to < today:
                issues.append(
                    ValidationIssue(
                        "team_id",
                        "inactive",
                        "error",
                        f"Trợ Lý AI: Tổ '{team.code}' không còn hiệu lực.",
                    )
                )

    return issues


def validate_employee_create(db: Session, body: EmployeeCreate) -> list[ValidationIssue]:
    team_id = body.team_id
    if team_id is None and body.team_code:
        from app.modules.mdm.service import resolve_employee_team

        try:
            team = resolve_employee_team(
                db, None, body.team_code, body.department_code, required=True
            )
            team_id = team.id if team else None
        except HTTPException as exc:
            detail = str(exc.detail)
            if "tổ" in detail.lower() or "team" in detail.lower():
                return [
                    ValidationIssue("team_id", "team_resolve", "error", detail),
                ]
            raise

    return _validate_common_fields(
        db,
        employee_code=body.employee_code,
        full_name=body.full_name,
        contract_salary=body.contract_salary,
        probation_salary=body.probation_salary,
        pay_channel=body.pay_channel,
        bank_account=body.bank_account,
        status=body.status,
        join_date=body.join_date,
        resign_date=body.resign_date,
        id_number=body.id_number,
        team_id=team_id,
        exclude_emp_id=None,
        require_code=True,
        require_name=True,
        require_salary=True,
        require_team=True,
    )


def validate_employee_update(
    db: Session, emp_id: UUID, body: EmployeeUpdate
) -> list[ValidationIssue]:
    emp = db.get(Employee, emp_id)
    if emp is None or emp.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy nhân viên.")

    data = body.model_dump(exclude_unset=True)
    team_id = data.get("team_id", emp.team_id)
    if "team_id" in data or "team_code" in data:
        from app.modules.mdm.service import resolve_employee_team

        try:
            team = resolve_employee_team(
                db,
                data.get("team_id"),
                data.get("team_code"),
                data.get("department_code"),
                required=False,
            )
            if team is not None:
                team_id = team.id
        except HTTPException as exc:
            return [ValidationIssue("team_id", "team_resolve", "error", str(exc.detail))]

    return _validate_common_fields(
        db,
        employee_code=None,
        full_name=data.get("full_name", emp.full_name),
        contract_salary=data.get("contract_salary", emp.contract_salary),
        probation_salary=data.get("probation_salary", emp.probation_salary),
        pay_channel=data.get("pay_channel", emp.pay_channel),
        bank_account=data.get("bank_account", emp.bank_account),
        status=data.get("status", emp.status),
        join_date=data.get("join_date", emp.join_date),
        resign_date=data.get("resign_date", emp.resign_date),
        id_number=data.get("id_number", emp.id_number),
        team_id=team_id,
        exclude_emp_id=emp_id,
        require_code=False,
        require_name="full_name" in data,
        require_salary="contract_salary" in data,
        require_team="team_id" in data or "team_code" in data,
    )


def _issues_from_pydantic(exc: ValidationError) -> list[ValidationIssue]:
    """Validate form dở — không 500; đổi lỗi schema thành tiếng Việt."""
    field_empty = {
        "full_name": "Trợ Lý AI: Họ tên không được để trống.",
        "employee_code": "Trợ Lý AI: MSNV không được để trống.",
    }
    issues: list[ValidationIssue] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = str(loc[-1] if loc else "payload")
        typ = str(err.get("type") or "invalid")
        if typ in ("string_too_short", "missing", "value_error.missing") and field in field_empty:
            msg = field_empty[field]
            code = "required"
        else:
            raw = str(err.get("msg") or "dữ liệu không hợp lệ.")
            msg = raw if raw.startswith("Trợ Lý AI") else f"Trợ Lý AI: {raw}"
            code = typ
        issues.append(ValidationIssue(field, code, "error", msg))
    return issues or [
        ValidationIssue("payload", "invalid", "error", "Trợ Lý AI: dữ liệu không hợp lệ."),
    ]


def validate_employee_payload(
    db: Session,
    *,
    is_new: bool,
    employee_id: UUID | None,
    payload: dict,
) -> list[ValidationIssue]:
    if is_new:
        try:
            body = EmployeeCreate.model_validate(payload)
        except ValidationError as exc:
            return _issues_from_pydantic(exc)
        return validate_employee_create(db, body)
    if employee_id is None:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: thiếu employee_id khi kiểm tra cập nhật.")
    try:
        body = EmployeeUpdate.model_validate(payload)
    except ValidationError as exc:
        return _issues_from_pydantic(exc)
    return validate_employee_update(db, employee_id, body)


def validation_result(issues: list[ValidationIssue]) -> dict:
    errors = [i for i in issues if i.level == "error"]
    return {
        "ok": len(errors) == 0,
        "issues": _issues_to_dict(issues),
        "error_count": len(errors),
        "warn_count": sum(1 for i in issues if i.level == "warn"),
    }
