"""
P3.5 — Hỗ trợ regression Oct/2025 (13§13.3).
Phân loại lệch so GenuiSuite: A (làm tròn) / B (logic sai) / C (ngoại lệ).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from app.modules.payroll.money import D

DiffClass = Literal["A", "B", "C", "OK"]


def classify_money_delta(
    dj_value: Decimal,
    genuisuite_value: Decimal | None,
    *,
    field: str,
    abs_tolerance_a: Decimal = Decimal("50"),
    marked_exception_c: bool = False,
) -> dict[str, Any]:
    """
    So DJ HRM vs số Excel GenuiSuite (nếu có).
    - OK: khớp từng đồng
    - A: |Δ| ≤ abs_tolerance_a (làm tròn cũ) — chấp nhận
    - C: đã đánh dấu ngoại lệ nghiệp vụ
    - B: lệch logic — không chấp nhận
    """
    if genuisuite_value is None:
        return {
            "field": field,
            "class": "OK",
            "dj": str(dj_value),
            "genuisuite": None,
            "delta": None,
            "note": "Không có số GenuiSuite để đối chiếu.",
        }
    dj = D(dj_value)
    gs = D(genuisuite_value)
    delta = dj - gs
    abs_d = abs(delta)
    if abs_d == 0:
        klass: DiffClass = "OK"
        note = "Khớp từng đồng."
    elif marked_exception_c:
        klass = "C"
        note = "Ngoại lệ nghiệp vụ (chờ/đã chốt HR)."
    elif abs_d <= abs_tolerance_a:
        klass = "A"
        note = "Lệch nhỏ — khả năng làm tròn GenuiSuite (chấp nhận)."
    else:
        klass = "B"
        note = "Lệch lớn — nghi ngờ sai công thức (không chấp nhận)."
    return {
        "field": field,
        "class": klass,
        "dj": str(dj),
        "genuisuite": str(gs),
        "delta": str(delta),
        "note": note,
    }


def summarize_classes(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"OK": 0, "A": 0, "B": 0, "C": 0}
    for r in rows:
        out[r["class"]] = out.get(r["class"], 0) + 1
    return out
