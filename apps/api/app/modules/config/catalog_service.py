"""Admin CRUD danh mục — loại nghỉ, khoản lương, lookup (2.8)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.attendance.models import LeaveType
from app.modules.audit.service import write_audit
from app.modules.config.catalog_schemas import (
    LeaveTypeAdminCreate,
    LeaveTypeAdminOut,
    LeaveTypeAdminUpdate,
    LookupValueAdminCreate,
    LookupValueAdminUpdate,
    PayComponentAdminCreate,
    PayComponentAdminOut,
    PayComponentAdminUpdate,
)
from app.modules.core.models import User
from app.modules.mdm.models import LookupValue
from app.modules.mdm.schemas import LookupValueOut
from app.modules.payroll.models import PayComponent


def _norm_code(code: str) -> str:
    return code.strip().upper()


def list_leave_types_admin(db: Session) -> list[LeaveTypeAdminOut]:
    rows = db.query(LeaveType).order_by(LeaveType.code.asc()).all()
    return [LeaveTypeAdminOut.model_validate(r) for r in rows]


def create_leave_type(db: Session, body: LeaveTypeAdminCreate, actor: User) -> LeaveTypeAdminOut:
    code = _norm_code(body.code)
    if db.get(LeaveType, code):
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: mã nghỉ '{code}' đã tồn tại.")
    if body.pay_ratio_percent is not None and body.pay_ratio_percent not in (0, 70, 100):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: pay_ratio_percent phải 0, 70, 100 hoặc để trống.")
    row = LeaveType(
        code=code,
        name=body.name.strip(),
        paid_by_company=body.paid_by_company,
        counts_as_unauthorized=body.counts_as_unauthorized,
        pay_ratio_percent=body.pay_ratio_percent,
        paid_by_si=body.paid_by_si,
        affects_attendance_bonus=body.affects_attendance_bonus,
        counts_as_worked_day=body.counts_as_worked_day,
        requires_document=body.requires_document,
        max_days_per_year=body.max_days_per_year,
    )
    db.add(row)
    write_audit(
        db,
        actor=actor,
        action="catalog.leave_type.create",
        entity_type="leave_types",
        entity_id=code,
        summary=f"Thêm loại nghỉ {code}",
        meta={"name": body.name},
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return LeaveTypeAdminOut.model_validate(row)


def update_leave_type(
    db: Session, code: str, body: LeaveTypeAdminUpdate, actor: User
) -> LeaveTypeAdminOut:
    row = db.get(LeaveType, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy loại nghỉ.")
    data = body.model_dump(exclude_unset=True)
    if "pay_ratio_percent" in data and data["pay_ratio_percent"] is not None:
        if data["pay_ratio_percent"] not in (0, 70, 100):
            raise HTTPException(status_code=400, detail="Trợ Lý AI: pay_ratio_percent phải 0, 70 hoặc 100.")
    for k, v in data.items():
        setattr(row, k, v)
    write_audit(
        db,
        actor=actor,
        action="catalog.leave_type.update",
        entity_type="leave_types",
        entity_id=code,
        summary=f"Cập nhật loại nghỉ {code}",
        meta=data,
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return LeaveTypeAdminOut.model_validate(row)


def list_pay_components_admin(db: Session) -> list[PayComponentAdminOut]:
    rows = db.query(PayComponent).order_by(PayComponent.code.asc()).all()
    return [PayComponentAdminOut.model_validate(r) for r in rows]


def create_pay_component(
    db: Session, body: PayComponentAdminCreate, actor: User
) -> PayComponentAdminOut:
    code = _norm_code(body.code)
    if db.query(PayComponent).filter(PayComponent.code == code).first():
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: mã khoản '{code}' đã tồn tại.")
    row = PayComponent(
        code=code,
        name=body.name.strip(),
        kind=body.kind,
        default_amount=Decimal(body.default_amount),
        proration=body.proration,
        proration_rule=body.proration_rule,
        include_in_si_base=body.include_in_si_base,
        include_in_ot_base=body.include_in_ot_base,
        affects_si_base=body.affects_si_base,
        affects_ot_base=body.affects_ot_base,
        affects_pit=body.affects_pit,
        is_active=True,
    )
    db.add(row)
    write_audit(
        db,
        actor=actor,
        action="catalog.pay_component.create",
        entity_type="pay_components",
        entity_id=code,
        summary=f"Thêm khoản lương {code}",
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return PayComponentAdminOut.model_validate(row)


def update_pay_component(
    db: Session, code: str, body: PayComponentAdminUpdate, actor: User
) -> PayComponentAdminOut:
    row = db.query(PayComponent).filter(PayComponent.code == code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy khoản lương.")
    data = body.model_dump(exclude_unset=True)
    if "default_amount" in data and data["default_amount"] is not None:
        data["default_amount"] = Decimal(data["default_amount"])
    for k, v in data.items():
        setattr(row, k, v)
    write_audit(
        db,
        actor=actor,
        action="catalog.pay_component.update",
        entity_type="pay_components",
        entity_id=code,
        summary=f"Cập nhật khoản {code}",
        meta=data,
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return PayComponentAdminOut.model_validate(row)


def list_lookup_admin(db: Session, group_code: str | None) -> list[LookupValueOut]:
    q = db.query(LookupValue)
    if group_code:
        q = q.filter(LookupValue.group_code == group_code.strip())
    rows = q.order_by(LookupValue.group_code.asc(), LookupValue.sort_order.asc()).all()
    return [LookupValueOut.model_validate(r) for r in rows]


def create_lookup(db: Session, body: LookupValueAdminCreate, actor: User) -> LookupValueOut:
    gc = body.group_code.strip()
    c = body.code.strip()
    exists = (
        db.query(LookupValue)
        .filter(LookupValue.group_code == gc, LookupValue.code == c)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: mã đã tồn tại trong nhóm.")
    row = LookupValue(
        group_code=gc,
        code=c,
        name=body.name.strip(),
        name_local=body.name_local,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    db.add(row)
    write_audit(
        db,
        actor=actor,
        action="catalog.lookup.create",
        entity_type="lookup_values",
        entity_id=f"{gc}:{c}",
        summary=f"Thêm lookup {gc}/{c}",
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return LookupValueOut.model_validate(row)


def update_lookup(
    db: Session, lookup_id: UUID, body: LookupValueAdminUpdate, actor: User
) -> LookupValueOut:
    row = db.get(LookupValue, lookup_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: không tìm thấy dòng lookup.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    write_audit(
        db,
        actor=actor,
        action="catalog.lookup.update",
        entity_type="lookup_values",
        entity_id=str(lookup_id),
        summary="Cập nhật lookup",
        meta=data,
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return LookupValueOut.model_validate(row)
