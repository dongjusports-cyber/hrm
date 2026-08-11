"""API policy packages — GET/PUT + X-Confirm-Step (file 08§8.2).

Hạng mục 2.5: thêm API đọc bảng chính sách có ngày hiệu lực (BH, thuế, thâm niên, chuyên cần).
Ghi/sửa các bảng đó thuộc hạng mục 2.8 (màn Admin).
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.core.deps import AdminUser, DbSession, require_module
from app.modules.core.models import User
from app.modules.policy import service
from app.modules.policy.schemas import (
    AttendanceBonusRuleOut,
    InsuranceRateOut,
    PitBracketOut,
    PitDeductionOut,
    PolicyConfirmPreview,
    PolicyPackageOut,
    PolicyPackageUpdate,
    SeniorityAllowanceTierOut,
    SeniorityAmountOut,
)

router = APIRouter(prefix="/policies/packages", tags=["policy"])
rates_router = APIRouter(prefix="/policies", tags=["policy-rates"])

HrUser = Annotated[User, Depends(require_module("hr"))]


@router.get("", response_model=list[PolicyPackageOut])
def list_packages(_admin: AdminUser, db: DbSession) -> list[PolicyPackageOut]:
    return service.list_packages(db)


@router.get("/{package_id}", response_model=PolicyPackageOut)
def get_package(package_id: UUID, _admin: AdminUser, db: DbSession) -> PolicyPackageOut:
    return service.to_out(service.get_package(db, package_id))


@router.put("/{package_id}", response_model=PolicyConfirmPreview)
def update_package(
    package_id: UUID,
    body: PolicyPackageUpdate,
    admin: AdminUser,
    db: DbSession,
    x_confirm_step: Annotated[int | None, Header(alias="X-Confirm-Step")] = None,
) -> PolicyConfirmPreview:
    # Phân biệt effective_to=null chủ động vs không gửi: Pydantic v2 model_fields_set
    clear_to = "effective_to" in body.model_fields_set and body.effective_to is None
    return service.update_package_with_confirm(
        db,
        actor=admin,
        package_id=package_id,
        confirm_step=x_confirm_step,
        name=body.name,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        clear_effective_to=clear_to,
        is_active=body.is_active,
        payload=body.payload,
    )


@rates_router.get("/insurance-rates/current", response_model=InsuranceRateOut)
def get_insurance_rate_current(
    _user: HrUser, db: DbSession, as_of: date | None = Query(default=None)
) -> InsuranceRateOut:
    """Tỷ lệ BHXH/BHYT/BHTN + công đoàn + trần nền tại ngày as_of (mặc định hôm nay)."""
    return service.get_insurance_rate(db, as_of)


@rates_router.get("/pit-brackets", response_model=list[PitBracketOut])
def get_pit_brackets(
    _user: HrUser, db: DbSession, as_of: date | None = Query(default=None)
) -> list[PitBracketOut]:
    """7 bậc thuế TNCN hiệu lực tại as_of."""
    return service.list_pit_brackets(db, as_of)


@rates_router.get("/pit-deductions/current", response_model=PitDeductionOut)
def get_pit_deduction_current(
    _user: HrUser, db: DbSession, as_of: date | None = Query(default=None)
) -> PitDeductionOut:
    return service.get_pit_deduction(db, as_of)


@rates_router.get("/seniority-tiers", response_model=list[SeniorityAllowanceTierOut])
def get_seniority_tiers(
    _user: HrUser, db: DbSession, as_of: date | None = Query(default=None)
) -> list[SeniorityAllowanceTierOut]:
    return service.list_seniority_tiers(db, as_of)


@rates_router.get("/seniority-amount", response_model=SeniorityAmountOut)
def get_seniority_amount(
    _user: HrUser,
    db: DbSession,
    months: int = Query(..., ge=0),
    as_of: date | None = Query(default=None),
) -> SeniorityAmountOut:
    """Tra tiền thâm niên theo số tháng — nghiệm thu: 136 → 550.000."""
    return service.lookup_seniority_amount(db, months, as_of)


@rates_router.get("/attendance-bonus-rules/current", response_model=AttendanceBonusRuleOut)
def get_attendance_bonus_rule_current(
    _user: HrUser, db: DbSession, as_of: date | None = Query(default=None)
) -> AttendanceBonusRuleOut:
    return service.get_attendance_bonus_rule(db, as_of)
