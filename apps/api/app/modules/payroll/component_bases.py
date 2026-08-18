"""Map mã GenusSuite (policy) ↔ catalog PayComponent."""

from __future__ import annotations

from decimal import Decimal

from app.modules.payroll.engine_allowances import AllowanceLine
from app.modules.payroll.money import D, ZERO

# 22§22.8 / 22§22.9 — tên cột Genus → mã HRM
GENUS_TO_CATALOG: dict[str, str | None] = {
    "BASIC": None,
    "POS": "POSITION",
    "TECH": "TECH",
    "TREAT": "TOXIC",
    "SENIORITY": "SENIORITY",
    "TRAIN": "TRAINING",
    "INDUS": "ATTEND",
    "PCCC": "PCCC",
    "HSE": "HSE",
}

_DEFAULT_OT_COMPONENTS = ["BASIC", "POS", "TECH", "TREAT", "SENIORITY", "TRAIN", "INDUS"]
# CTY: lương HĐ + chức vụ + độc hại + tay nghề + thâm niên + PCCC + HSE (không đào tạo).
_DEFAULT_SI_COMPONENTS = ["BASIC", "POS", "TECH", "TREAT", "SENIORITY", "PCCC", "HSE"]


def apply_si_base_cap(si_base: Decimal, policy: dict) -> tuple[Decimal, Decimal | None]:
    """22§22.9 — trần nền BHXH từ policy.si_base_cap."""
    cap_raw = (policy or {}).get("si_base_cap")
    if cap_raw is None:
        return D(si_base), None
    cap = D(cap_raw)
    base = D(si_base)
    if base > cap:
        return cap, base
    return base, None


def sum_policy_components(
    component_codes: list[str],
    *,
    contract_salary: Decimal,
    lines_by_code: dict[str, AllowanceLine],
    attend_full_monthly: Decimal,
) -> Decimal:
    total = ZERO
    for raw in component_codes:
        code = str(raw).strip().upper()
        if code == "BASIC":
            total += D(contract_salary)
            continue
        if code == "INDUS":
            total += D(attend_full_monthly)
            continue
        catalog = GENUS_TO_CATALOG.get(code)
        if catalog is None and code in lines_by_code:
            catalog = code
        if catalog and catalog in lines_by_code:
            total += D(lines_by_code[catalog].monthly_full)
    return total


def compute_si_and_ot_bases(
    *,
    contract_salary: Decimal,
    allowance_lines: list[AllowanceLine],
    attend_full_monthly: Decimal,
    policy: dict,
) -> tuple[Decimal, Decimal, dict]:
    """Trả (si_base, ot_base, breakdown)."""
    lines_by_code = {ln.code: ln for ln in allowance_lines}
    ot_codes = list((policy or {}).get("ot_base_components") or _DEFAULT_OT_COMPONENTS)
    si_codes = list((policy or {}).get("si_base_components") or _DEFAULT_SI_COMPONENTS)
    si_base = sum_policy_components(
        si_codes,
        contract_salary=contract_salary,
        lines_by_code=lines_by_code,
        attend_full_monthly=attend_full_monthly,
    )
    ot_base = sum_policy_components(
        ot_codes,
        contract_salary=contract_salary,
        lines_by_code=lines_by_code,
        attend_full_monthly=attend_full_monthly,
    )
    breakdown = {
        "si_base_components": si_codes,
        "ot_base_components": ot_codes,
        "si_base": str(si_base),
        "ot_base": str(ot_base),
    }
    return si_base, ot_base, breakdown
