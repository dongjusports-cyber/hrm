"""Policy package service — P10 xác nhận 3 lần khi sửa tiền."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.core.models import User
from app.modules.policy.models import PolicyConfirmLog, PolicyPackage
from app.modules.policy.schemas import (
    AttendanceBonusRuleOut,
    InsuranceRateOut,
    PitBracketOut,
    PitDeductionOut,
    PolicyConfirmPreview,
    PolicyPackageOut,
    SeniorityAllowanceTierOut,
    SeniorityAmountOut,
)
from app.modules.policy.seed_payload import default_payload, normalize_si_policy
from app.modules.policy.validator import money_field_diffs, validate_payload


def to_out(pkg: PolicyPackage) -> PolicyPackageOut:
    return PolicyPackageOut.model_validate(pkg)


def list_packages(db: Session) -> list[PolicyPackageOut]:
    rows = db.query(PolicyPackage).order_by(PolicyPackage.effective_from.desc()).all()
    return [to_out(r) for r in rows]


def get_package(db: Session, package_id: UUID) -> PolicyPackage:
    pkg = db.get(PolicyPackage, package_id)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trợ Lý AI: không tìm thấy gói policy.",
        )
    return pkg


def seed_default_package(db: Session) -> PolicyPackage:
    from app.modules.policy.seed_rates import seed_policy_rate_tables

    seed_policy_rate_tables(db)
    existing = db.query(PolicyPackage).filter(PolicyPackage.name == "Mặc định 2025").first()
    if existing:
        existing.payload = normalize_si_policy(existing.payload if isinstance(existing.payload, dict) else {})
        db.commit()
        db.refresh(existing)
        return existing
    pkg = PolicyPackage(
        name="Mặc định 2025",
        effective_from=date(2025, 1, 1),
        effective_to=None,
        is_active=True,
        payload=default_payload(),
        version=1,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


def update_package_with_confirm(
    db: Session,
    *,
    actor: User,
    package_id: UUID,
    confirm_step: int | None,
    name: str | None,
    effective_from: date | None,
    effective_to: date | None,
    clear_effective_to: bool,
    is_active: bool | None,
    payload: dict[str, Any],
) -> PolicyConfirmPreview:
    if confirm_step not in (1, 2, 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Trợ Lý AI: sửa tham số tiền cần xác nhận 3 bước. "
                "Gửi header X-Confirm-Step: 1, rồi 2, rồi 3."
            ),
        )

    pkg = get_package(db, package_id)
    clean = validate_payload(payload)
    money_changed = money_field_diffs(pkg.payload or {}, clean)

    if confirm_step == 1:
        detail = (
            f"Trợ Lý AI xin chào {actor.full_name}, đây là bước 1/3. "
            "Bạn sắp thay đổi gói policy ảnh hưởng lương/BH. "
            f"Các nhóm tiền thay đổi: {', '.join(money_changed) if money_changed else 'không (chỉ metadata/rule)'}."
        )
        return PolicyConfirmPreview(
            step=1,
            status="need_confirm",
            detail=detail,
            changed_money_fields=money_changed,
            package=None,
        )

    if confirm_step == 2:
        detail = (
            f"Trợ Lý AI xin chào {actor.full_name}, đây là bước 2/3. "
            "Xác nhận lần nữa: thay đổi sẽ áp dụng cho kỳ lương mới (phiếu đã khóa không tự sửa). "
            "Bấm bước 3 chỉ khi bạn chắc chắn."
        )
        return PolicyConfirmPreview(
            step=2,
            status="need_confirm",
            detail=detail,
            changed_money_fields=money_changed,
            package=None,
        )

    before = dict(pkg.payload or {})
    if name is not None:
        pkg.name = name.strip()
    if effective_from is not None:
        pkg.effective_from = effective_from
    if clear_effective_to:
        pkg.effective_to = None
    elif effective_to is not None:
        pkg.effective_to = effective_to
    if is_active is not None:
        pkg.is_active = is_active

    pkg.payload = clean
    pkg.version = int(pkg.version or 1) + 1

    db.add(
        PolicyConfirmLog(
            package_id=pkg.id,
            actor_user_id=actor.id,
            confirm_step=3,
            before_payload=before,
            after_payload=clean,
            note=f"money_fields={','.join(money_changed)}",
        )
    )
    db.commit()
    db.refresh(pkg)
    from app.modules.audit.service import write_audit

    write_audit(
        db,
        actor=actor,
        action="policy.save_confirmed",
        entity_type="policy_package",
        entity_id=str(pkg.id),
        summary=f"Lưu policy «{pkg.name}» v{pkg.version} sau 3 bước xác nhận",
        meta={"version": pkg.version, "money_fields_count": len(money_changed)},
    )

    return PolicyConfirmPreview(
        step=3,
        status="saved",
        detail=(
            f"Trợ Lý AI xin chào {actor.full_name}, đã lưu gói policy «{pkg.name}» "
            f"(phiên bản {pkg.version}) sau 3 bước xác nhận."
        ),
        changed_money_fields=money_changed,
        package=to_out(pkg),
    )


def _effective_filter(model, as_of: date):
    """effective_from ≤ as_of và (effective_to IS NULL hoặc effective_to ≥ as_of)."""
    return [
        model.effective_from <= as_of,
        or_(model.effective_to.is_(None), model.effective_to >= as_of),
    ]


def get_insurance_rate(db: Session, as_of: date | None = None) -> InsuranceRateOut:
    from app.modules.policy.seed_rates import seed_policy_rate_tables
    from app.modules.policy.models import InsuranceRate

    seed_policy_rate_tables(db)
    day = as_of or date.today()
    row = (
        db.query(InsuranceRate)
        .filter(*_effective_filter(InsuranceRate, day))
        .order_by(InsuranceRate.effective_from.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: chưa có tỷ lệ bảo hiểm hiệu lực.")
    return InsuranceRateOut.model_validate(row)


def list_pit_brackets(db: Session, as_of: date | None = None) -> list[PitBracketOut]:
    from app.modules.policy.seed_rates import seed_policy_rate_tables
    from app.modules.policy.models import PitBracket

    seed_policy_rate_tables(db)
    day = as_of or date.today()
    latest_from = (
        db.query(PitBracket.effective_from)
        .filter(*_effective_filter(PitBracket, day))
        .order_by(PitBracket.effective_from.desc())
        .limit(1)
        .scalar()
    )
    if latest_from is None:
        return []
    rows = (
        db.query(PitBracket)
        .filter(PitBracket.effective_from == latest_from)
        .order_by(PitBracket.seq.asc())
        .all()
    )
    return [PitBracketOut.model_validate(r) for r in rows]


def get_pit_deduction(db: Session, as_of: date | None = None) -> PitDeductionOut:
    from app.modules.policy.seed_rates import seed_policy_rate_tables
    from app.modules.policy.models import PitDeduction

    seed_policy_rate_tables(db)
    day = as_of or date.today()
    row = (
        db.query(PitDeduction)
        .filter(*_effective_filter(PitDeduction, day))
        .order_by(PitDeduction.effective_from.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: chưa có mức giảm trừ TNCN hiệu lực.")
    return PitDeductionOut.model_validate(row)


def list_seniority_tiers(db: Session, as_of: date | None = None) -> list[SeniorityAllowanceTierOut]:
    from app.modules.policy.seed_rates import seed_policy_rate_tables
    from app.modules.policy.models import SeniorityAllowanceTier

    seed_policy_rate_tables(db)
    day = as_of or date.today()
    latest_from = (
        db.query(SeniorityAllowanceTier.effective_from)
        .filter(*_effective_filter(SeniorityAllowanceTier, day))
        .order_by(SeniorityAllowanceTier.effective_from.desc())
        .limit(1)
        .scalar()
    )
    if latest_from is None:
        return []
    rows = (
        db.query(SeniorityAllowanceTier)
        .filter(SeniorityAllowanceTier.effective_from == latest_from)
        .order_by(SeniorityAllowanceTier.months_from.asc())
        .all()
    )
    return [SeniorityAllowanceTierOut.model_validate(r) for r in rows]


def lookup_seniority_amount(
    db: Session, months: int, as_of: date | None = None
) -> SeniorityAmountOut:
    """Tra bậc thâm niên theo số tháng — nghiệm thu đợt 2: 136 tháng → 550.000."""
    from decimal import Decimal

    if months < 0:
        raise HTTPException(
            status_code=400, detail="Trợ Lý AI: số tháng thâm niên không được âm."
        )
    day = as_of or date.today()
    tiers = list_seniority_tiers(db, day)
    for t in tiers:
        upper_ok = t.months_to is None or months <= t.months_to
        if t.months_from <= months and upper_ok:
            return SeniorityAmountOut(
                months=months,
                as_of=day,
                amount=t.amount,
                months_from=t.months_from,
                months_to=t.months_to,
            )
    return SeniorityAmountOut(
        months=months, as_of=day, amount=Decimal("0"), months_from=0, months_to=None
    )


def get_attendance_bonus_rule(db: Session, as_of: date | None = None) -> AttendanceBonusRuleOut:
    from app.modules.policy.seed_rates import seed_policy_rate_tables
    from app.modules.policy.models import AttendanceBonusRule

    seed_policy_rate_tables(db)
    day = as_of or date.today()
    row = (
        db.query(AttendanceBonusRule)
        .filter(*_effective_filter(AttendanceBonusRule, day))
        .order_by(AttendanceBonusRule.effective_from.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Trợ Lý AI: chưa có quy tắc chuyên cần hiệu lực.")
    return AttendanceBonusRuleOut.model_validate(row)
