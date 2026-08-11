"""Validator payload có kiểm soát — không nhận SQL/công thức tự do (quyết định 10.7#12)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.modules.policy.seed_payload import MONEY_TOP_KEYS, default_payload

REQUIRED_TOP_KEYS = set(default_payload().keys())

_LEGACY_WRONG_EXEMPT_LEAVE = frozenset({"AL", "MARRIAGE", "FUNERAL", "HEALTHCHECK"})


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: payload phải là object JSON.",
        )

    # Chặn khóa lạ nguy hiểm (trên input gốc)
    forbidden = {"sql", "raw_sql", "formula_code", "eval", "script"}
    lower_keys = {str(k).lower() for k in payload}
    hit = forbidden & lower_keys
    if hit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trợ Lý AI: không được nhập SQL/công thức tự do trong policy.",
        )

    # Gói cũ thiếu khóa mới (KPI…) → điền mặc định, không phá save
    merged = default_payload()
    merged.update(payload)
    payload = merged

    missing = REQUIRED_TOP_KEYS - set(payload.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trợ Lý AI: thiếu khóa bắt buộc trong payload: {', '.join(sorted(missing))}.",
        )

    _require_number(payload, "union_fee_default")
    _require_number(payload, "attendance_bonus_monthly")
    _require_number(payload, "transport_monthly_default")
    _require_int(payload, "payslip_confirm_days", min_v=1, max_v=60)

    ot = payload.get("ot_rates")
    if not isinstance(ot, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: ot_rates phải là object.")
    for k in ("weekday", "weekend", "holiday"):
        if k not in ot:
            raise HTTPException(status_code=400, detail=f"Trợ Lý AI: thiếu ot_rates.{k}.")
        _as_number(ot[k], f"ot_rates.{k}")
    if ot.get("sunday") is not None:
        _as_number(ot["sunday"], "ot_rates.sunday")
    if ot.get("holiday_over_8") is not None:
        _as_number(ot["holiday_over_8"], "ot_rates.holiday_over_8")

    prob = payload.get("probation")
    if prob is not None:
        if not isinstance(prob, dict):
            raise HTTPException(status_code=400, detail="Trợ Lý AI: probation phải là object.")
        if "salary_percent" in prob:
            pct = _as_number(prob["salary_percent"], "probation.salary_percent")
            if pct <= 0 or pct > 100:
                raise HTTPException(
                    status_code=400,
                    detail="Trợ Lý AI: probation.salary_percent phải từ 1–100.",
                )
        if "zero_allowances" in prob and not isinstance(prob["zero_allowances"], bool):
            raise HTTPException(status_code=400, detail="Trợ Lý AI: probation.zero_allowances phải bool.")

    si = payload.get("si_rates")
    if not isinstance(si, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: si_rates phải là object.")
    for k in ("bhxh", "bhyt", "bhtn"):
        if k not in si:
            raise HTTPException(status_code=400, detail=f"Trợ Lý AI: thiếu si_rates.{k}.")
        val = _as_number(si[k], f"si_rates.{k}")
        if val < 0 or val > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Trợ Lý AI: si_rates.{k} phải trong khoảng 0–1 (ví dụ 0.08).",
            )

    if payload.get("si_base_cap") is not None:
        cap = _as_number(payload["si_base_cap"], "si_base_cap")
        if cap <= 0:
            raise HTTPException(status_code=400, detail="Trợ Lý AI: si_base_cap phải > 0.")

    if not isinstance(payload.get("ot_night_enabled"), bool):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: ot_night_enabled phải là true/false.")

    if not isinstance(payload.get("pit_enabled"), bool):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: pit_enabled phải là true/false.")
    _require_number(payload, "pit_personal_deduction")
    _require_number(payload, "pit_dependent_deduction")
    brackets = payload.get("pit_brackets")
    if not isinstance(brackets, list) or not brackets:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: pit_brackets phải là mảng biểu thuế.")
    for i, b in enumerate(brackets):
        if not isinstance(b, dict) or "rate" not in b:
            raise HTTPException(status_code=400, detail=f"Trợ Lý AI: pit_brackets[{i}] thiếu rate.")
        rate = _as_number(b["rate"], f"pit_brackets[{i}].rate")
        if rate < 0 or rate > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Trợ Lý AI: pit_brackets[{i}].rate phải trong 0–1.",
            )
        if b.get("up_to") is not None:
            _as_number(b["up_to"], f"pit_brackets[{i}].up_to")

    divisor = payload.get("divisor_rule")
    if not isinstance(divisor, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: divisor_rule không hợp lệ.")
    has_cap = divisor.get("source") == "calendar_working_days" and divisor.get("cap") is not None
    has_legacy = "when_official_eq" in divisor and "use_divisor" in divisor
    if not has_cap and not has_legacy:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: divisor_rule cần source+cap hoặc when_official_eq+use_divisor.",
        )
    if has_cap:
        cap = _as_number(divisor["cap"], "divisor_rule.cap")
        if cap <= 0 or cap > 31:
            raise HTTPException(status_code=400, detail="Trợ Lý AI: divisor_rule.cap phải 1–31.")

    penalties = payload.get("attendance_penalties")
    if not isinstance(penalties, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: attendance_penalties phải là object.")
    _validate_attendance_penalties(penalties)

    proration = payload.get("allowance_proration")
    if proration is not None and not isinstance(proration, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: allowance_proration phải là object.")

    work_time = payload.get("work_time")
    if work_time is not None and not isinstance(work_time, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: work_time phải là object.")

    annual = payload.get("annual_leave")
    if annual is not None and not isinstance(annual, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: annual_leave phải là object.")

    rounding = payload.get("rounding")
    if rounding is not None and not isinstance(rounding, dict):
        raise HTTPException(status_code=400, detail="Trợ Lý AI: rounding phải là object.")

    # KPI ngưỡng — None = tắt / dùng mặc định runtime
    if payload.get("kpi_manpower_factor") is not None:
        b3 = _as_number(payload["kpi_manpower_factor"], "kpi_manpower_factor")
        if b3 <= 0 or b3 > 31:
            raise HTTPException(
                status_code=400,
                detail="Trợ Lý AI: kpi_manpower_factor phải từ 0+ đến 31 (hoặc null).",
            )
    _require_number(payload, "kpi_hours_per_day")
    hours = _as_number(payload["kpi_hours_per_day"], "kpi_hours_per_day")
    if hours <= 0 or hours > 24:
        raise HTTPException(status_code=400, detail="Trợ Lý AI: kpi_hours_per_day phải 0–24.")
    for key in (
        "kpi_attendance_min_pct",
        "kpi_ot_rate_max_pct",
        "kpi_turnover_max_pct",
        "kpi_ot_dept_max_pct",
    ):
        pct = _as_number(payload[key], key)
        if pct < 0 or pct > 100:
            raise HTTPException(status_code=400, detail=f"Trợ Lý AI: {key} phải từ 0–100.")

    return payload


def _validate_attendance_penalties(penalties: dict[str, Any]) -> None:
    exempt = penalties.get("exempt_leave_codes")
    if exempt is not None:
        if not isinstance(exempt, list):
            raise HTTPException(
                status_code=400,
                detail="Trợ Lý AI: exempt_leave_codes phải là mảng mã nghỉ.",
            )
        bad = _LEGACY_WRONG_EXEMPT_LEAVE & {str(x).upper() for x in exempt}
        if bad:
            raise HTTPException(
                status_code=400,
                detail="Trợ Lý AI: mã miễn trừ chuyên cần phải là ALE / FLE / WED "
                f"(không dùng {', '.join(sorted(bad))}).",
            )

    uses_v2 = penalties.get("late_half") is not None or penalties.get("late_zero") is not None
    uses_legacy = bool(penalties.get("late") or penalties.get("early_or_absent_group"))
    if not uses_v2 and not uses_legacy:
        raise HTTPException(
            status_code=400,
            detail="Trợ Lý AI: attendance_penalties thiếu ngưỡng (late_half/… hoặc late/…).",
        )

    if uses_v2:
        for key in ("late_half", "early_half", "late_zero", "early_zero"):
            if key not in penalties:
                raise HTTPException(status_code=400, detail=f"Trợ Lý AI: thiếu attendance_penalties.{key}.")
            num = _as_number(penalties[key], f"attendance_penalties.{key}")
            if int(num) != num:
                raise HTTPException(
                    status_code=400,
                    detail=f"Trợ Lý AI: attendance_penalties.{key} phải là số nguyên.",
                )
            if num < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Trợ Lý AI: attendance_penalties.{key} phải >= 0.",
                )
        if "any_absence_zero" in penalties and not isinstance(penalties["any_absence_zero"], bool):
            raise HTTPException(status_code=400, detail="Trợ Lý AI: any_absence_zero phải bool.")
        if penalties.get("exempt_requires_hours_lt") is not None:
            hrs = _as_number(penalties["exempt_requires_hours_lt"], "exempt_requires_hours_lt")
            if hrs <= 0 or hrs > 24:
                raise HTTPException(
                    status_code=400,
                    detail="Trợ Lý AI: exempt_requires_hours_lt phải 0–24.",
                )
        if "exempt_requires_punch" in penalties and not isinstance(penalties["exempt_requires_punch"], bool):
            raise HTTPException(status_code=400, detail="Trợ Lý AI: exempt_requires_punch phải bool.")
        if "ignore_absence_during_probation" in penalties and not isinstance(
            penalties["ignore_absence_during_probation"], bool
        ):
            raise HTTPException(
                status_code=400,
                detail="Trợ Lý AI: ignore_absence_during_probation phải bool.",
            )


def money_field_diffs(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for key in sorted(MONEY_TOP_KEYS):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def _require_number(payload: dict, key: str) -> float:
    if key not in payload:
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: thiếu {key}.")
    return _as_number(payload[key], key)


def _require_int(payload: dict, key: str, min_v: int, max_v: int) -> int:
    val = _require_number(payload, key)
    if int(val) != val:
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: {key} phải là số nguyên.")
    iv = int(val)
    if iv < min_v or iv > max_v:
        raise HTTPException(
            status_code=400,
            detail=f"Trợ Lý AI: {key} phải từ {min_v} đến {max_v}.",
        )
    return iv


def _as_number(val: Any, label: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise HTTPException(status_code=400, detail=f"Trợ Lý AI: {label} phải là số.")
    return float(val)
