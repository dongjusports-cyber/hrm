"""Mẫu dòng phiếu lương GenusSuite — worker mobile (WK-I004).

Luôn hiện đủ slot; thiếu dữ liệu → amount/quantity null (UI «—»).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.payroll.payslip_detail import _day_target

_EMPTY_AMOUNT: Decimal | None = None


@dataclass(frozen=True)
class GenusSlot:
    label: str
    codes: tuple[str, ...] = ()
    unit: str | None = None
    ot_note_types: tuple[str, ...] = ()
    adjust_kinds: tuple[str, ...] = ()
    merge_codes: bool = False


def _empty_line(slot: GenusSlot, salary_divisor: Decimal | None) -> dict:
    return {
        "label": slot.label,
        "amount": _EMPTY_AMOUNT,
        "quantity": None,
        "unit": slot.unit,
        "target": _day_target(salary_divisor, slot.unit) if slot.unit else None,
        "component_code": slot.codes[0] if slot.codes else "",
        "note": None,
    }


def _line_from_slot(slot: GenusSlot, ln: dict, salary_divisor: Decimal | None) -> dict:
    unit = ln.get("unit") or slot.unit
    return {
        "label": slot.label,
        "amount": ln.get("amount"),
        "quantity": ln.get("quantity"),
        "unit": unit,
        "target": ln.get("target") if ln.get("target") is not None else _day_target(
            salary_divisor, unit
        ),
        "component_code": ln.get("component_code", ""),
        "note": ln.get("note"),
    }


def _note_lower(ln: dict) -> str:
    note = ln.get("note") or ""
    label = ln.get("label") or ""
    return f"{note} {label}".lower()


def _match_slot(ln: dict, slot: GenusSlot) -> bool:
    code = str(ln.get("component_code") or "").upper()
    if slot.ot_note_types:
        if code != "OT":
            return False
        text = _note_lower(ln)
        if any(t in text for t in slot.ot_note_types):
            return True
        # OT gộp «Tăng ca» không ghi loại → coi là tăng ca thường
        if slot.ot_note_types == ("weekday",) and not any(
            x in text for x in ("weekend", "sunday", "holiday", "night")
        ):
            return True
        return False
    if slot.adjust_kinds:
        if code != "ADJUST":
            return False
        amt = ln.get("amount")
        if amt is None:
            return False
        n = Decimal(str(amt))
        if "addon" in slot.adjust_kinds and n > 0:
            return True
        if "deduct" in slot.adjust_kinds and n < 0:
            return True
        return False
    if slot.codes and code in slot.codes:
        return True
    return False


def apply_genus_template(
    actual: list[dict],
    slots: list[GenusSlot],
    salary_divisor: Decimal | None,
) -> list[dict]:
    used: set[int] = set()
    out: list[dict] = []

    for slot in slots:
        matched_idx: list[int] = []
        for i, ln in enumerate(actual):
            if i in used:
                continue
            if _match_slot(ln, slot):
                matched_idx.append(i)

        if not matched_idx:
            out.append(_empty_line(slot, salary_divisor))
            continue

        if slot.merge_codes or len(matched_idx) > 1:
            total = Decimal("0")
            qty: Decimal | None = None
            unit = slot.unit
            for i in matched_idx:
                used.add(i)
                ln = actual[i]
                total += Decimal(str(ln.get("amount") or 0))
                if ln.get("quantity") is not None:
                    q = Decimal(str(ln["quantity"]))
                    qty = (qty or Decimal("0")) + q
                if ln.get("unit"):
                    unit = ln.get("unit")
            if total == 0 and qty is None:
                out.append(_empty_line(slot, salary_divisor))
            else:
                out.append(
                    {
                        "label": slot.label,
                        "amount": total if total != 0 else _EMPTY_AMOUNT,
                        "quantity": qty,
                        "unit": unit,
                        "target": _day_target(salary_divisor, unit),
                        "component_code": ",".join(slot.codes),
                        "note": None,
                    }
                )
            continue

        i = matched_idx[0]
        used.add(i)
        out.append(_line_from_slot(slot, actual[i], salary_divisor))

    return out


WORK_SLOTS: list[GenusSlot] = [
    GenusSlot("Ngày công", codes=("WD",), unit="day"),
    GenusSlot("Tăng ca thường", codes=("OT",), unit="hour", ot_note_types=("weekday",)),
    GenusSlot("Tăng ca ngày nghỉ", codes=("OT",), unit="hour", ot_note_types=("weekend", "sunday")),
    GenusSlot(
        "Tăng ca ngày lễ",
        codes=("OT",),
        unit="hour",
        ot_note_types=("holiday", "holiday_over"),
    ),
    GenusSlot("Trợ cấp ca đêm", codes=("OT",), unit="hour", ot_note_types=("night", "night_nt")),
]

LEAVE_SLOTS: list[GenusSlot] = [
    GenusSlot("Nghỉ phép năm", codes=("ALE",), unit="day"),
    GenusSlot("Nghỉ chế độ", codes=("MLE", "MC", "REM", "PT"), unit="day"),
    GenusSlot("Nghỉ lễ", codes=("PH", "HOL", "OFF"), unit="day"),
    GenusSlot("Nghỉ hưởng lương", codes=("SLE", "FLE", "WED", "SCH"), unit="day"),
]

ALLOWANCE_SLOTS: list[GenusSlot] = [
    GenusSlot("TC Chuyên cần", codes=("ATTEND",), unit="day"),
    GenusSlot("TC Chức vụ", codes=("POSITION",), unit="day"),
    GenusSlot("TC độc hại", codes=("TOXIC",), unit="day"),
    GenusSlot("TC Đi lại", codes=("TRANSPORT",), unit="day"),
    GenusSlot("TC Tay nghề may", codes=("TECH",), unit="day"),
    GenusSlot("TC Thâm niên", codes=("SENIORITY",), unit="month"),
    GenusSlot("TC Khác", codes=("OTHER",), unit="day"),
    GenusSlot("Thưởng", codes=("BONUS",)),
    GenusSlot("Hoàn trả tháng trước", codes=("ADJUST",), adjust_kinds=("addon",)),
    GenusSlot("PCCC + HSE", codes=("PCCC", "HSE"), unit="day", merge_codes=True),
]

DEDUCTION_SLOTS: list[GenusSlot] = [
    GenusSlot("KT BHYT", codes=("BHYT",)),
    GenusSlot("KT BHXH", codes=("BHXH",)),
    GenusSlot("KT BHTN", codes=("BHTN",)),
    GenusSlot("Phí công đoàn", codes=("UNION",)),
    GenusSlot("KT tháng trước", codes=("ADVANCE", "ADJUST"), adjust_kinds=("deduct",)),
    GenusSlot("KT Khác", codes=("OTHER_DED", "DEDUCT")),
    GenusSlot("Thuế TNCN", codes=("PIT",)),
]


def apply_genus_work_template(lines: list[dict], salary_divisor: Decimal | None) -> list[dict]:
    return apply_genus_template(lines, WORK_SLOTS, salary_divisor)


def apply_genus_leave_template(lines: list[dict], salary_divisor: Decimal | None) -> list[dict]:
    return apply_genus_template(lines, LEAVE_SLOTS, salary_divisor)


def apply_genus_allowance_template(lines: list[dict], salary_divisor: Decimal | None) -> list[dict]:
    return apply_genus_template(lines, ALLOWANCE_SLOTS, salary_divisor)


def apply_genus_deduction_template(lines: list[dict], salary_divisor: Decimal | None) -> list[dict]:
    return apply_genus_template(lines, DEDUCTION_SLOTS, salary_divisor)


_DAY_UNITS = frozenset({"day", "days", "ngày"})


def fill_missing_day_quantity(lines: list[dict], worked_days: Decimal | None) -> None:
    """Cột CT (ngày) — chỉ điền khi đã có tiền mà engine chưa ghi quantity.

    Không đụng dòng trống («—») và không ghi đè số ngày đã có.
    """
    if worked_days is None:
        return
    for ln in lines:
        if ln.get("amount") is None:
            continue
        unit = str(ln.get("unit") or "").lower()
        if unit in _DAY_UNITS and ln.get("quantity") is None:
            ln["quantity"] = worked_days
