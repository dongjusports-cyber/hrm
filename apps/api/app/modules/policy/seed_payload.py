"""

Seed payload mặc định — nguồn: HIEN_PHAP 22§22.12 + 03/07 (KPI, pit, night OT).

Runtime payroll đọc từ DB — không import hằng số này vào công thức tính lương.

"""



from copy import deepcopy

from typing import Any



DEFAULT_POLICY_PAYLOAD: dict[str, Any] = {

    "attendance_bonus_monthly": 600_000,

    "transport_monthly_default": 800_000,

    "probation": {"salary_percent": 85, "zero_allowances": True},

    "divisor_rule": {

        "source": "calendar_working_days",

        "cap": 26,

        # Giữ khóa legacy để gói cũ / test tương thích; calendar ưu tiên source+cap.

        "when_official_eq": 27,

        "use_divisor": 26,

        "else": "official",

    },

    "allowance_proration": {

        "numerator": ["WT", "ALE", "FLE", "WED", "HOL", "COM"],

        "formula": "base / divisor * numerator_days",

    },

    "attendance_penalties": {

        "late_half": 2,

        "early_half": 2,

        "late_zero": 5,

        "early_zero": 5,

        "any_absence_zero": True,

        "exempt_leave_codes": ["ALE", "FLE", "WED"],

        "exempt_requires_hours_lt": 8,

        "exempt_requires_punch": True,

        "ignore_absence_during_probation": True,

        "penalty_leave_codes": ["NOP", "NON"],

    },

    "work_time": {

        "standard_shift": {"start": "08:00:00", "end": "17:00:00"},

        "lunch_deduct_hours": 1,

        "punches_per_day": 2,

        "night_shift_enabled": False,

        "late_grace_seconds": 0,

        "early_grace_seconds": 0,

        "punch_dedupe": {"window_seconds": 60},

    },

    "ot_split": {

        "on_books_weekdays": [2, 4],

        "ot_grace_minutes": 15,

        "on_books_after": "17:15",

        "on_books_until": "20:00",

        "note": "Bấm ra sau 17h15 mới có OT; số phút OT tính từ 17h00. Th3+Th5: 17h-20h sổ; sau 20h → ngoài.",

        "ot_external": {

            "rate_key": "weekday",

            "exclude_from_payslip": True,

            "payment_channel": "ATM",

            "note": "Cùng công thức 22§22.8 (ot_base) — trả theo phút, không BHXH/PIT trên payslip chính.",

        },

    },

    "ot_rates": {

        "weekday": 1.5,

        "weekend": 2.0,

        "sunday": 2.0,

        "holiday": 2.0,

        "holiday_over_8": 3.0,

        "night_addon": 0.3,

        "ot_night_extra": 0.2,

    },

    "ot_night_enabled": False,

    "ot_base_components": ["BASIC", "POS", "TECH", "TREAT", "SENIORITY", "TRAIN", "INDUS"],

    "si_rates": {"bhxh": 0.08, "bhyt": 0.015, "bhtn": 0.01},

    "si_base_components": ["BASIC", "POS", "TECH", "SENIORITY", "TRAIN", "TREAT"],

    "si_base_cap": 46_800_000,

    "union_fee_default": 44_100,

    "annual_leave": {

        "days_per_year": 14,

        "extra_day_every_years": 5,

        "accrual_mode": "monthly_prorated",

        "accrual_round_digits": 2,

        "payout_divisor": 26,

    },

    "pit_enabled": False,

    "pit_personal_deduction": 11_000_000,

    "pit_dependent_deduction": 4_400_000,

    "pit_brackets": [

        {"up_to": 5_000_000, "rate": 0.05},

        {"up_to": 10_000_000, "rate": 0.10},

        {"up_to": 18_000_000, "rate": 0.15},

        {"up_to": 32_000_000, "rate": 0.20},

        {"up_to": 52_000_000, "rate": 0.25},

        {"up_to": 80_000_000, "rate": 0.30},

        {"up_to": None, "rate": 0.35},

    ],

    "rounding": {

        "money_unit": 1,

        "money_mode": "half_up",

        "hours_step_minutes": 1,

        "hours_mode": "floor",

        "day_fraction_digits": 2,

    },

    "payslip_confirm_days": 7,

    "kpi_manpower_factor": None,

    "kpi_hours_per_day": 8,

    "kpi_attendance_min_pct": 90,

    "kpi_ot_rate_max_pct": 20,

    "kpi_turnover_max_pct": 5,

    "kpi_ot_dept_max_pct": 30,

}



# Khóa liên quan tiền — dùng cho cảnh báo P10

MONEY_TOP_KEYS = {

    "union_fee_default",

    "attendance_bonus_monthly",

    "transport_monthly_default",

    "ot_rates",

    "si_rates",

    "si_base_cap",

    "pit_enabled",

    "pit_personal_deduction",

    "pit_dependent_deduction",

    "pit_brackets",

}





def default_payload() -> dict[str, Any]:

    return deepcopy(DEFAULT_POLICY_PAYLOAD)


