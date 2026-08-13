"""
P3.2 — Phụ cấp + phạt chuyên cần (03§3.4).
Số tiền policy/catalog truyền từ ngoài — không hard-code trong công thức.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.modules.payroll.allowance_proration import compute_numerator_days, prorate_allowance
from app.modules.payroll.money import D, ZERO, money_vnd

# Quy định CTY 2026-08: có gán trên hồ sơ → trả đủ tháng (không ÷ ngày công).
# OTHER («Khác»): phụ cấp ĐT và khoản lẻ — HR tự nhập số tiền từng người.
FULL_MONTH_IF_ASSIGNED = frozenset({"PCCC", "HSE", "TOXIC", "TECH", "OTHER"})


@dataclass(frozen=True)
class AllowanceTypeView:
    code: str
    name: str
    proration: str
    include_in_si_base: bool
    include_in_ot_base: bool
    default_amount: Decimal
    rules: dict | None = None


@dataclass
class AllowanceLine:
    code: str
    name: str
    monthly_full: Decimal
    amount: Decimal
    include_in_si_base: bool
    include_in_ot_base: bool
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AllowanceInput:
    salary_divisor: Decimal
    worked_days: Decimal
    late_count: int
    early_count: int
    # Ngày nghỉ tính phạt chuyên cần (UA/UL/SICK…) — không gồm AL/REM exempt
    penalty_absent_days: Decimal
    join_date: date | None
    as_of: date
    policy: dict[str, Any]
    # code → monthly amount (đã resolve assignment/default)
    monthly_by_code: dict[str, Decimal]
    types: list[AllowanceTypeView]
    child_count_under_6: int = 0
    # 4.3 — ngày nghỉ theo mã (ALE/FLE/WED/OFF…) để tính tử số chia phụ cấp
    leave_days_by_code: dict[str, Decimal] | None = None
    detail_days_by_category: dict[str, Decimal] | None = None
    # 4.4 — audit miễn trừ trễ/sớm (F_CAL_INDUS_AMT)
    penalty_audit: dict | None = None
    # 4.2 / 22§22.3 — tháng thử việc thuần: chuyên cần, đi lại và phụ cấp = 0
    suppress_allowances: bool = False


@dataclass(frozen=True)
class AllowanceResult:
    lines: list[AllowanceLine]
    allowance_total: Decimal
    attend_keep_percent: int
    # Giá trị đầy đủ ATTEND (trước phạt) — dùng base OT (P3.3)
    attend_full_monthly: Decimal
    numerator_days: Decimal
    detail: dict


def attendance_keep_percent(
    *,
    late_count: int,
    early_count: int,
    absent_days: Decimal,
    penalties: dict[str, Any],
) -> int:
    """% còn lại của chuyên cần (22§22.3 / Genus F_CAL_INDUS_AMT)."""
    absent = D(absent_days)

    # Payload 22.12 — ba điều kiện độc lập (50% rồi 0% ghi đè)
    if penalties.get("late_half") is not None or penalties.get("late_zero") is not None:
        late_half = int(penalties.get("late_half", 3))
        early_half = int(penalties.get("early_half", 2))
        late_zero = int(penalties.get("late_zero", 5))
        early_zero = int(penalties.get("early_zero", 4))
        keep = 100
        if late_count >= late_half or early_count >= early_half:
            keep = 50
        if late_count >= late_zero or early_count >= early_zero:
            keep = 0
        if penalties.get("any_absence_zero", True) and absent > 0:
            keep = 0
        return max(0, min(100, keep))

    keeps: list[int] = [100]

    for rule in penalties.get("late") or []:
        lo = int(rule.get("min", 0))
        hi = int(rule.get("max", 999))
        if lo <= late_count <= hi:
            keeps.append(int(rule.get("keep_percent", 100)))

    for rule in penalties.get("early_or_absent_group") or []:
        if "absent_days_gte" in rule and absent >= D(rule["absent_days_gte"]):
            keeps.append(int(rule.get("keep_percent", 100)))
            continue
        need_absent = rule.get("absent_days")
        need_early = rule.get("or_early_times")
        hit = False
        if need_absent is not None and absent >= D(need_absent):
            hit = True
        if need_early is not None and early_count >= int(need_early):
            hit = True
        if hit:
            keeps.append(int(rule.get("keep_percent", 100)))

    mode = (penalties.get("penalty_combine_mode") or "min_keep").lower()
    if mode == "multiply":
        pct = 100
        for k in keeps:
            if k == 100:
                continue
            pct = int(Decimal(pct) * Decimal(k) / Decimal(100))
        return max(0, min(100, pct))
    return max(0, min(100, min(keeps)))


def seniority_monthly(join_date: date | None, as_of: date, rules: dict | None) -> Decimal:
    if join_date is None:
        return ZERO
    months = (as_of.year - join_date.year) * 12 + (as_of.month - join_date.month)
    if as_of.day < join_date.day:
        months -= 1
    if months < 0:
        months = 0

    tiers = (rules or {}).get("tiers") or []
    # Fixed high tiers first
    for tier in tiers:
        if "fixed" in tier:
            lo = int(tier.get("min_months", 0))
            hi = int(tier.get("max_months", 10_000))
            if lo <= months < hi or (hi >= 10_000 and months >= lo):
                return D(tier["fixed"])

    # Progressive: base + per_6_months after first 6 months in band
    for tier in tiers:
        if "per_6_months" in tier or "base" in tier:
            lo = int(tier.get("min_months", 0))
            hi = int(tier.get("max_months", 120))
            if lo <= months < hi:
                base = D(tier.get("base", 0))
                step = D(tier.get("per_6_months", 0))
                # Đủ 6 tháng → base; mỗi thêm 6 tháng + step
                extra_blocks = max(0, (months - lo) // 6)
                return base + step * Decimal(extra_blocks)
    return ZERO


def prorate_by_worked(monthly: Decimal, divisor: Decimal, worked_days: Decimal) -> Decimal:
    """Legacy alias — 4.3 dùng prorate_allowance + numerator_days."""
    return prorate_allowance(monthly, divisor, worked_days)


def should_zero_probation_allowances(
    policy: dict[str, Any] | None,
    *,
    contract_signed_at: date | None,
    period_to: date,
) -> bool:
    """Thử việc thuần cả kỳ (chưa ký HĐ hoặc ký sau kỳ) + policy.probation.zero_allowances."""
    prob = (policy or {}).get("probation") or {}
    if not bool(prob.get("zero_allowances", False)):
        return False
    return contract_signed_at is None or contract_signed_at > period_to


def compute_allowances(inp: AllowanceInput) -> AllowanceResult:
    policy = inp.policy or {}
    penalties = policy.get("attendance_penalties") or {}
    keep = attendance_keep_percent(
        late_count=inp.late_count,
        early_count=inp.early_count,
        absent_days=inp.penalty_absent_days,
        penalties=penalties,
    )
    divisor = D(inp.salary_divisor)
    worked = D(inp.worked_days)
    leave_map = inp.leave_days_by_code or {}
    detail_map = inp.detail_days_by_category or {}
    numerator, numerator_parts = compute_numerator_days(
        worked_days=worked,
        leave_days_by_code=leave_map,
        detail_days_by_category=detail_map,
        policy=policy,
    )
    lines: list[AllowanceLine] = []
    attend_full = ZERO

    type_map = {t.code: t for t in inp.types}

    # ATTEND — luôn từ policy nếu có type
    if "ATTEND" in type_map:
        t = type_map["ATTEND"]
        monthly = inp.monthly_by_code.get(
            "ATTEND",
            D(policy.get("attendance_bonus_monthly", t.default_amount)),
        )
        attend_full = D(monthly)
        raw = prorate_allowance(attend_full, divisor, numerator)
        final = money_vnd(raw * Decimal(keep) / Decimal(100))
        lines.append(
            AllowanceLine(
                code="ATTEND",
                name=t.name,
                monthly_full=attend_full,
                amount=final,
                include_in_si_base=t.include_in_si_base,
                include_in_ot_base=t.include_in_ot_base,
                detail={
                    "raw": str(raw),
                    "keep_percent": keep,
                    "numerator_days": str(numerator),
                    "numerator_parts": numerator_parts,
                    "late_count": inp.late_count,
                    "early_count": inp.early_count,
                    "penalty_absent_days": str(inp.penalty_absent_days),
                    **(inp.penalty_audit or {}),
                },
            )
        )

    if "TRANSPORT" in type_map:
        t = type_map["TRANSPORT"]
        monthly = inp.monthly_by_code.get(
            "TRANSPORT",
            D(policy.get("transport_monthly_default", t.default_amount)),
        )
        amt = money_vnd(prorate_allowance(D(monthly), divisor, numerator))
        lines.append(
            AllowanceLine(
                code="TRANSPORT",
                name=t.name,
                monthly_full=D(monthly),
                amount=amt,
                include_in_si_base=t.include_in_si_base,
                include_in_ot_base=t.include_in_ot_base,
                detail={
                    "proration": "by_numerator_days",
                    "numerator_days": str(numerator),
                    "numerator_parts": numerator_parts,
                },
            )
        )

    if "SENIORITY" in type_map:
        t = type_map["SENIORITY"]
        monthly = inp.monthly_by_code.get("SENIORITY")
        if monthly is None:
            monthly = seniority_monthly(inp.join_date, inp.as_of, t.rules)
        # Thâm niên thường full tháng (Excel) — full_if_eligible
        amt = money_vnd(D(monthly))
        if amt > 0:
            lines.append(
                AllowanceLine(
                    code="SENIORITY",
                    name=t.name,
                    monthly_full=D(monthly),
                    amount=amt,
                    include_in_si_base=t.include_in_si_base,
                    include_in_ot_base=t.include_in_ot_base,
                    detail={"join_date": str(inp.join_date) if inp.join_date else None},
                )
            )

    if "CHILD" in type_map and inp.child_count_under_6 > 0:
        t = type_map["CHILD"]
        per = inp.monthly_by_code.get("CHILD", t.default_amount)
        monthly = D(per) * Decimal(inp.child_count_under_6)
        lines.append(
            AllowanceLine(
                code="CHILD",
                name=t.name,
                monthly_full=monthly,
                amount=money_vnd(monthly),
                include_in_si_base=t.include_in_si_base,
                include_in_ot_base=t.include_in_ot_base,
                detail={"children": inp.child_count_under_6},
            )
        )

    # Các mã gán tay: POSITION, TOXIC, PCCC, TECH, OTHER…
    skip = {"ATTEND", "TRANSPORT", "SENIORITY", "CHILD"}
    for code, monthly in inp.monthly_by_code.items():
        if code in skip or code not in type_map:
            continue
        t = type_map[code]
        m = D(monthly)
        if m <= 0:
            continue
        if t.proration == "by_worked_days" and code not in FULL_MONTH_IF_ASSIGNED:
            amt = money_vnd(prorate_allowance(m, divisor, numerator))
        else:
            amt = money_vnd(m)
        lines.append(
            AllowanceLine(
                code=code,
                name=t.name,
                monthly_full=m,
                amount=amt,
                include_in_si_base=t.include_in_si_base,
                include_in_ot_base=t.include_in_ot_base,
                detail={
                    "proration": t.proration,
                    "numerator_days": str(numerator) if t.proration == "by_worked_days" else None,
                },
            )
        )

    if inp.suppress_allowances and lines:
        lines = [
            AllowanceLine(
                code=ln.code,
                name=ln.name,
                monthly_full=ln.monthly_full,
                amount=ZERO,
                include_in_si_base=ln.include_in_si_base,
                include_in_ot_base=ln.include_in_ot_base,
                detail={**(ln.detail or {}), "zeroed": "probation.zero_allowances"},
            )
            for ln in lines
        ]
        attend_full = ZERO

    total = money_vnd(sum((ln.amount for ln in lines), ZERO))
    return AllowanceResult(
        lines=lines,
        allowance_total=total,
        attend_keep_percent=keep,
        attend_full_monthly=attend_full,
        numerator_days=numerator,
        detail={
            "count": len(lines),
            "attend_keep_percent": keep,
            "numerator_days": str(numerator),
            "numerator_parts": numerator_parts,
            "salary_divisor": str(divisor),
            "suppress_allowances": inp.suppress_allowances,
            "items": [
                {"code": ln.code, "amount": str(ln.amount), "monthly_full": str(ln.monthly_full)}
                for ln in lines
            ],
        },
    )
