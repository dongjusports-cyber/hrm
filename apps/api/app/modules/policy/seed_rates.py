"""Seed 5 bảng chính sách có ngày hiệu lực (hạng mục 2.5).

Nguồn số:
- BH / công đoàn / trần: 22§22.9 + GenusSuite GenuiSuite_Logic.sql dòng 13410–13420
- Biểu thuế + giảm trừ: seed_payload hiện hành + 22§22.10 / 22§22.12
- Thâm niên: 22§22.5 + F_CAL_SERVERANCE (bung công thức 6–119 thành bậc 6 tháng)
- Chuyên cần: 20§20.7 (600.000) + F_CAL_INDUS_AMT (ngưỡng 3/2 → 5/4) + 22§22.12

effective_from mặc định = 2024-07-01 (mốc lương tối thiểu vùng I NĐ 74/2024) — đủ bao phủ
dữ liệu GenusSuite Jan–Jul/2026. effective_to = NULL (đang hiệu lực).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.policy.models import (
    AttendanceBonusRule,
    InsuranceRate,
    PitBracket,
    PitDeduction,
    SeniorityAllowanceTier,
)

SEED_FROM = date(2024, 7, 1)


def _seniority_tiers_rows() -> list[tuple[int, int | None, Decimal]]:
    """(months_from, months_to, amount) — bung F_CAL_SERVERANCE thành dữ liệu phẳng."""
    rows: list[tuple[int, int | None, Decimal]] = [(0, 5, Decimal("0"))]
    # 6–119: FLOOR(tháng/6)×25.000 → mỗi khối 6 tháng một dòng
    for start in range(6, 120, 6):
        end = min(start + 5, 119)
        amount = Decimal(start // 6 * 25_000)
        rows.append((start, end, amount))
    rows.append((120, 191, Decimal("550000")))
    rows.append((192, 251, Decimal("600000")))
    rows.append((252, 371, Decimal("650000")))
    rows.append((372, None, Decimal("700000")))
    return rows


def seed_policy_rate_tables(db: Session) -> dict[str, int]:
    """Nạp nếu còn trống — không ghi đè dòng HR đã sửa (giống seed_lookup_values)."""
    created: dict[str, int] = {
        "insurance_rates": 0,
        "pit_brackets": 0,
        "pit_deductions": 0,
        "seniority_allowance_tiers": 0,
        "attendance_bonus_rules": 0,
    }

    if db.query(InsuranceRate).count() == 0:
        db.add(
            InsuranceRate(
                effective_from=SEED_FROM,
                effective_to=None,
                si_employee_pct=Decimal("8"),
                hi_employee_pct=Decimal("1.5"),
                ui_employee_pct=Decimal("1"),
                union_pct=Decimal("44100"),  # số tiền cố định — lệch tên cột (xem báo cáo)
                si_base_cap=Decimal("46800000"),
                # Lương tối thiểu vùng — Chủ chốt 4.730.000 (2026-08-11); seed mặc định cho DB mới.
                region_min_wage=Decimal("4730000"),
            )
        )
        created["insurance_rates"] = 1

    if db.query(PitBracket).filter(PitBracket.effective_from == SEED_FROM).count() == 0:
        brackets = [
            (1, Decimal("0"), Decimal("5")),
            (2, Decimal("5000000"), Decimal("10")),
            (3, Decimal("10000000"), Decimal("15")),
            (4, Decimal("18000000"), Decimal("20")),
            (5, Decimal("32000000"), Decimal("25")),
            (6, Decimal("52000000"), Decimal("30")),
            (7, Decimal("80000000"), Decimal("35")),
        ]
        for seq, from_amt, rate in brackets:
            db.add(
                PitBracket(
                    effective_from=SEED_FROM,
                    effective_to=None,
                    seq=seq,
                    from_amount=from_amt,
                    rate_percent=rate,
                )
            )
        created["pit_brackets"] = len(brackets)

    if db.query(PitDeduction).count() == 0:
        db.add(
            PitDeduction(
                effective_from=SEED_FROM,
                effective_to=None,
                self_amount=Decimal("11000000"),
                dependent_amount=Decimal("4400000"),
            )
        )
        created["pit_deductions"] = 1

    if db.query(SeniorityAllowanceTier).filter(SeniorityAllowanceTier.effective_from == SEED_FROM).count() == 0:
        for months_from, months_to, amount in _seniority_tiers_rows():
            db.add(
                SeniorityAllowanceTier(
                    effective_from=SEED_FROM,
                    effective_to=None,
                    months_from=months_from,
                    months_to=months_to,
                    amount=amount,
                )
            )
        created["seniority_allowance_tiers"] = len(_seniority_tiers_rows())

    if db.query(AttendanceBonusRule).count() == 0:
        db.add(
            AttendanceBonusRule(
                effective_from=SEED_FROM,
                effective_to=None,
                late_count_half=3,
                early_count_half=2,
                late_count_zero=5,
                early_count_zero=4,
                exempt_leave_codes=["ALE", "FLE", "WED"],
                full_amount=Decimal("600000"),
            )
        )
        created["attendance_bonus_rules"] = 1

    if any(created.values()):
        db.commit()
    return created
