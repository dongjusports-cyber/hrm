"""

Seed payload mặc định — nguồn: thư mục Luật/ (HR đọc, sai thì sửa đó).

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

        "ot_grace_minutes": 30,

        "on_books_after": "17:30",

        "on_books_until": "20:00",

        "ignore_punches_from": "17:00",

        "ignore_punches_until": "17:30",

        "note": "Luật OT: Luật/02-OT.md. OT trong Th3+Th5 17–20; còn lại OT ngoài. Tiền theo phút.",

        "ot_external": {

            "rate_key": "weekday",

            "exclude_from_payslip": True,

            "payment_channel": "ATM",

            "note": "OT ngoài theo khung giờ công ty (x1,5/x2,1 ngày thường · CN x2/x3,5/x4,1 · lễ x3/x4,5/x5,1) — không vào payslip/BHXH/PIT, chi ATM riêng.",

        },

    },

    "ot_rates": {

        "weekday": 1.5,

        "weekend": 2.0,

        "sunday": 2.0,

        "holiday": 2.0,

        "holiday_over_8": 3.0,

        "night_addon": 0.6,

        "ot_night_extra": 0.2,

        "use_time_bands": True,

        "bands": {

            "weekday": {"night": "2.1", "shoulder": "1.5", "core": "0", "evening": "1.5"},

            "sunday": {"night": "4.1", "shoulder": "3.5", "core": "2.0", "evening": "3.5"},

            "holiday": {"night": "5.1", "shoulder": "4.5", "core": "3.0", "evening": "4.5"},

        },

    },

    "ot_night_enabled": False,

    "ot_base_components": ["BASIC", "POS", "TECH", "TREAT", "SENIORITY", "TRAIN", "INDUS"],

    "si_rates": {"bhxh": 0.08, "bhyt": 0.015, "bhtn": 0.01},

    "si_base_components": ["BASIC", "POS", "TECH", "TREAT", "SENIORITY", "PCCC", "HSE"],

    "si_month_rule": {"min_worked_days": 12, "from_day_of_month": 16},

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


def normalize_si_policy(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Gói Policy cũ: thêm luật tháng 12 ngày / ngày 16; nền BHXH CTY (PCCC+HSE, bỏ Đào tạo)."""
    defaults = default_payload()
    out = dict(payload or {})
    for k, v in defaults.items():
        if k not in out:
            out[k] = deepcopy(v)
    codes = [str(c).strip().upper() for c in (out.get("si_base_components") or [])]
    if "TRAIN" in codes or "PCCC" not in codes or "HSE" not in codes:
        out["si_base_components"] = list(defaults["si_base_components"])
    if not isinstance(out.get("si_month_rule"), dict):
        out["si_month_rule"] = dict(defaults["si_month_rule"])
    out["ot_split"] = _normalize_ot_split(out.get("ot_split"), defaults["ot_split"])
    rnd = out.get("rounding")
    if isinstance(rnd, dict) and "hours_step_minutes" not in rnd:
        rnd["hours_step_minutes"] = defaults["rounding"]["hours_step_minutes"]
    return out


def _normalize_ot_split(raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    """Gói cũ: ngưỡng toilet 17:15 → nghỉ cơm 17:00–17:30; phút OT vẫn từ 17:00."""
    ot = dict(defaults)
    if isinstance(raw, dict):
        ot.update(raw)
    after = str(ot.get("on_books_after") or "")
    try:
        grace = int(ot.get("ot_grace_minutes", 30))
    except (TypeError, ValueError):
        grace = 30
    if after.startswith("17:15") or grace == 15:
        ot["on_books_after"] = defaults["on_books_after"]
        ot["ot_grace_minutes"] = defaults["ot_grace_minutes"]
        ot["note"] = defaults.get("note", ot.get("note"))
    ot.setdefault("ignore_punches_from", defaults.get("ignore_punches_from", "17:00"))
    ot.setdefault("ignore_punches_until", defaults.get("ignore_punches_until", "17:30"))
    return ot


