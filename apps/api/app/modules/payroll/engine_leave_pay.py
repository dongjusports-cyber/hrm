"""
4.2 — Lương ngày nghỉ (22§22.6).

tiền = (BASIC_SAL + SAL_ALLOW) / divisor × số_ngày × (% trả / 100)
Mỗi mã nghỉ một dòng — tách segment official | probation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.modules.payroll.engine_wd import WdSalaryInput, split_days_by_contract
from app.modules.payroll.money import D, ZERO, money_vnd


@dataclass(frozen=True)
class LeaveTypePayMeta:
    code: str
    name: str
    pay_ratio_percent: int | None


@dataclass(frozen=True)
class LeavePayLine:
    leave_code: str
    leave_name: str
    segment: str
    days: Decimal
    pay_ratio_percent: int
    amount: Decimal
    seq_no: int = 1


@dataclass(frozen=True)
class LeavePayInput:
    contract_salary: Decimal
    probation_salary: Decimal
    sal_allow: Decimal
    salary_divisor: Decimal
    wd_context: WdSalaryInput
    # leave_code → tổng ngày nghỉ (từ điều chỉnh / bảng công)
    leave_days_by_code: dict[str, Decimal]
    leave_types: dict[str, LeaveTypePayMeta]


@dataclass(frozen=True)
class LeavePayResult:
    lines: list[LeavePayLine]
    leave_pay_total: Decimal
    detail: dict = field(default_factory=dict)


def _daily_rate(base_salary: Decimal, sal_allow: Decimal, divisor: Decimal) -> Decimal:
    if divisor <= 0:
        return ZERO
    return (D(base_salary) + D(sal_allow)) / divisor


def compute_leave_pay(inp: LeavePayInput) -> LeavePayResult:
    lines: list[LeavePayLine] = []
    skipped: list[dict] = []
    seq_by_key: dict[tuple[str, str], int] = {}

    for code, raw_days in sorted(inp.leave_days_by_code.items()):
        days = D(raw_days)
        if days <= 0:
            continue
        meta = inp.leave_types.get(code)
        if meta is None:
            skipped.append({"code": code, "reason": "unknown_leave_code"})
            continue
        if meta.pay_ratio_percent is None:
            skipped.append({"code": code, "reason": "pay_ratio_not_set"})
            continue
        ratio = int(meta.pay_ratio_percent)
        if ratio <= 0:
            continue

        off_days, pro_days = split_days_by_contract(days, inp.wd_context)
        segments: list[tuple[str, Decimal, Decimal]] = []
        if off_days > 0:
            segments.append(
                (
                    "official",
                    off_days,
                    _daily_rate(inp.contract_salary, inp.sal_allow, inp.salary_divisor),
                )
            )
        if pro_days > 0:
            segments.append(
                (
                    "probation",
                    pro_days,
                    _daily_rate(inp.probation_salary, inp.sal_allow, inp.salary_divisor),
                )
            )

        for segment, seg_days, daily in segments:
            raw_amt = daily * seg_days * Decimal(ratio) / Decimal("100")
            amt = money_vnd(raw_amt)
            if amt <= 0:
                continue
            key = (code, segment)
            seq_by_key[key] = seq_by_key.get(key, 0) + 1
            lines.append(
                LeavePayLine(
                    leave_code=code,
                    leave_name=meta.name,
                    segment=segment,
                    days=seg_days,
                    pay_ratio_percent=ratio,
                    amount=amt,
                    seq_no=seq_by_key[key],
                )
            )

    total = money_vnd(sum((ln.amount for ln in lines), ZERO))
    return LeavePayResult(
        lines=lines,
        leave_pay_total=total,
        detail={
            "formula": "(basic+sal_allow)/divisor*days*pay_ratio/100",
            "sal_allow": str(D(inp.sal_allow)),
            "lines": [
                {
                    "code": ln.leave_code,
                    "segment": ln.segment,
                    "days": str(ln.days),
                    "ratio": ln.pay_ratio_percent,
                    "amount": str(ln.amount),
                }
                for ln in lines
            ],
            "skipped": skipped,
            "leave_pay_total": str(total),
        },
    )
