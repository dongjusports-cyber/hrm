"""Sổ phép năm — bút toán (4.7, 22§22.7)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.attendance.models import (
    AnnualLeaveEntry,
    AnnualLeaveLedger,
    LeaveRequest,
    PayPeriod,
    TimesheetMonth,
)
from app.modules.mdm.models import Employee
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload

Q2 = Decimal("0.01")
KIND_ACCRUAL = "accrual"
KIND_USE = "use"
KIND_ADJUST = "adjust"
KIND_PAYOUT = "payout"


def _al_policy(db: Session) -> tuple[int, int]:
    """(mốc NV mới, số năm thì +1 ngày). Thiếu key trên gói cũ → 14 và 5."""
    fallback_base = int(default_payload()["annual_leave"]["days_per_year"])
    fallback_every = int(default_payload()["annual_leave"].get("extra_day_every_years") or 5)
    pkg = (
        db.query(PolicyPackage)
        .filter(PolicyPackage.is_active.is_(True))
        .order_by(PolicyPackage.effective_from.desc())
        .first()
    )
    base, every = fallback_base, fallback_every
    if pkg and isinstance(pkg.payload, dict):
        al = pkg.payload.get("annual_leave")
        if isinstance(al, dict):
            try:
                base = int(al.get("days_per_year", fallback_base))
            except (TypeError, ValueError):
                base = fallback_base
            raw_every = al.get("extra_day_every_years", fallback_every)
            try:
                every = int(raw_every) if raw_every not in (None, "") else fallback_every
            except (TypeError, ValueError):
                every = fallback_every
    return base, max(0, every)


def _annual_days_per_year(db: Session) -> int:
    """Mốc phép NV mới (không gồm thâm niên)."""
    return _al_policy(db)[0]


def entitled_days_per_year(emp: Employee, as_of: date, base: int, extra_every: int) -> int:
    """Mốc năm = 14 + 1 mỗi đủ 5 năm thâm niên (theo ngày vào)."""
    if extra_every <= 0 or emp.join_date is None:
        return base
    years = as_of.year - emp.join_date.year
    if (as_of.month, as_of.day) < (emp.join_date.month, emp.join_date.day):
        years -= 1
    years = max(0, years)
    return base + years // extra_every


def entitled_days_for(db: Session, emp: Employee, as_of: date) -> int:
    base, every = _al_policy(db)
    return entitled_days_per_year(emp, as_of, base, every)


def _signed_days(kind: str, days: Decimal) -> Decimal:
    raw = abs(days).quantize(Q2, rounding=ROUND_HALF_UP)
    if kind in (KIND_USE, KIND_PAYOUT):
        return -raw
    if kind == KIND_ACCRUAL:
        return raw
    return days.quantize(Q2, rounding=ROUND_HALF_UP)


def ensure_ledger(db: Session, employee_id: UUID, year: int) -> AnnualLeaveLedger:
    row = (
        db.query(AnnualLeaveLedger)
        .filter(AnnualLeaveLedger.employee_id == employee_id, AnnualLeaveLedger.year == year)
        .one_or_none()
    )
    if row is not None:
        return row
    row = AnnualLeaveLedger(
        employee_id=employee_id,
        year=year,
        opening_balance=Decimal("0"),
        accrued=Decimal("0"),
        used=Decimal("0"),
        adjusted=Decimal("0"),
        closing_balance=Decimal("0"),
    )
    db.add(row)
    db.flush()
    return row


def _entry_exists(db: Session, ledger_id: UUID, reference: str) -> bool:
    return (
        db.query(AnnualLeaveEntry.id)
        .filter(AnnualLeaveEntry.ledger_id == ledger_id, AnnualLeaveEntry.reference == reference)
        .first()
        is not None
    )


def _refresh_ledger_summary(db: Session, ledger: AnnualLeaveLedger) -> None:
    _refresh_ledger_summary_batch(db, [ledger])


def _refresh_ledger_summary_batch(db: Session, ledgers: list[AnnualLeaveLedger]) -> None:
    """Tính lại tổng sổ từ bút toán — một query cho cả lô, dùng ở đường lệnh."""
    if not ledgers:
        return
    by_id = {led.id: led for led in ledgers}
    rows = db.query(AnnualLeaveEntry).filter(AnnualLeaveEntry.ledger_id.in_(list(by_id))).all()
    agg: dict[UUID, dict] = {
        led_id: {
            "accrued": Decimal("0"),
            "used": Decimal("0"),
            "adjusted": Decimal("0"),
            "movement": Decimal("0"),
            "last_accrual_month": None,
        }
        for led_id in by_id
    }
    for row in rows:
        bucket = agg.get(row.ledger_id)
        if bucket is None:
            continue
        signed = _signed_days(row.kind, row.days)
        bucket["movement"] += signed
        if row.kind == KIND_ACCRUAL:
            bucket["accrued"] += abs(signed)
            bucket["last_accrual_month"] = max(
                bucket["last_accrual_month"] or 0, row.entry_date.month
            )
        elif row.kind == KIND_USE:
            bucket["used"] += abs(signed)
        elif row.kind == KIND_ADJUST:
            bucket["adjusted"] += signed
    for led_id, ledger in by_id.items():
        bucket = agg[led_id]
        ledger.accrued = bucket["accrued"].quantize(Q2, rounding=ROUND_HALF_UP)
        ledger.used = bucket["used"].quantize(Q2, rounding=ROUND_HALF_UP)
        ledger.adjusted = bucket["adjusted"].quantize(Q2, rounding=ROUND_HALF_UP)
        ledger.closing_balance = (ledger.opening_balance + bucket["movement"]).quantize(
            Q2, rounding=ROUND_HALF_UP
        )
        ledger.last_accrued_month = bucket["last_accrual_month"]


def add_entry(
    db: Session,
    ledger: AnnualLeaveLedger,
    *,
    kind: str,
    days: Decimal,
    entry_date: date,
    reference: str | None = None,
    note: str = "",
) -> AnnualLeaveEntry | None:
    if reference and _entry_exists(db, ledger.id, reference):
        return None
    signed = _signed_days(kind, days)
    if signed == 0:
        return None
    row = AnnualLeaveEntry(
        ledger_id=ledger.id,
        entry_date=entry_date,
        kind=kind,
        days=abs(days).quantize(Q2, rounding=ROUND_HALF_UP),
        reference=reference,
        note=note,
    )
    db.add(row)
    db.flush()
    _refresh_ledger_summary(db, ledger)
    return row


def _accrual_months(emp: Employee, as_of: date) -> int:
    year_start = date(as_of.year, 1, 1)
    accrual_start = year_start
    if emp.join_date and emp.join_date > accrual_start:
        accrual_start = emp.join_date
    if accrual_start > as_of:
        return 0
    months = (as_of.year - accrual_start.year) * 12 + (as_of.month - accrual_start.month) + 1
    return max(0, min(12, months))


def sync_accrual(db: Session, emp: Employee, as_of: date) -> AnnualLeaveLedger:
    """Đồng bộ tích lũy phép đến tháng của `as_of` — round(months × days/12, 2)."""
    ledger = ensure_ledger(db, emp.id, as_of.year)
    months = _accrual_months(emp, as_of)
    if months <= 0:
        return ledger
    days_per_year = entitled_days_for(db, emp, as_of)
    target = (Decimal(months) * Decimal(days_per_year) / Decimal(12)).quantize(
        Q2, rounding=ROUND_HALF_UP
    )
    current = ledger.accrued
    delta = (target - current).quantize(Q2, rounding=ROUND_HALF_UP)
    if delta > 0:
        add_entry(
            db,
            ledger,
            kind=KIND_ACCRUAL,
            days=delta,
            entry_date=as_of,
            reference=f"accrual-{as_of.year}-through-{months:02d}",
            note=f"Tích lũy đến tháng {months}/{as_of.year}",
        )
    return ledger


def record_leave_use(
    db: Session,
    *,
    employee_id: UUID,
    leave_request_id: UUID,
    days: Decimal,
    entry_date: date,
) -> None:
    emp = db.get(Employee, employee_id)
    if emp is None:
        return
    ledger = sync_accrual(db, emp, entry_date)
    add_entry(
        db,
        ledger,
        kind=KIND_USE,
        days=days,
        entry_date=entry_date,
        reference=f"leave_request:{leave_request_id}",
        note="Duyệt đơn phép năm",
    )


def ledger_balance_from_entries(db: Session, ledger_id: UUID) -> Decimal:
    ledger = db.get(AnnualLeaveLedger, ledger_id)
    if ledger is None:
        return Decimal("0")
    rows = db.query(AnnualLeaveEntry).filter(AnnualLeaveEntry.ledger_id == ledger_id).all()
    movement = sum(_signed_days(r.kind, r.days) for r in rows)
    return (ledger.opening_balance + movement).quantize(Q2, rounding=ROUND_HALF_UP)


def pending_submitted_days(db: Session, employee_id: UUID, year: int) -> Decimal:
    used = (
        db.query(func.coalesce(func.sum(LeaveRequest.total_days), 0))
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_code == "ALE",
            LeaveRequest.status == "submitted",
            LeaveRequest.from_date >= date(year, 1, 1),
            LeaveRequest.from_date <= date(year, 12, 31),
        )
        .scalar()
    )
    return Decimal(str(used or 0)).quantize(Q2, rounding=ROUND_HALF_UP)


def pending_submitted_days_batch(
    db: Session, employee_ids: list[UUID], year: int
) -> dict[UUID, Decimal]:
    """Tổng ngày ALE chờ duyệt theo NV — 1 query (Bước H)."""
    if not employee_ids:
        return {}
    rows = (
        db.query(
            LeaveRequest.employee_id,
            func.coalesce(func.sum(LeaveRequest.total_days), 0),
        )
        .filter(
            LeaveRequest.employee_id.in_(employee_ids),
            LeaveRequest.leave_type_code == "ALE",
            LeaveRequest.status == "submitted",
            LeaveRequest.from_date >= date(year, 1, 1),
            LeaveRequest.from_date <= date(year, 12, 31),
        )
        .group_by(LeaveRequest.employee_id)
        .all()
    )
    return {
        emp_id: Decimal(str(total or 0)).quantize(Q2, rounding=ROUND_HALF_UP)
        for emp_id, total in rows
    }


def _target_accrued(emp: Employee, as_of: date, days_per_year: int) -> Decimal:
    months = _accrual_months(emp, as_of)
    if months <= 0:
        return Decimal("0")
    return (Decimal(months) * Decimal(days_per_year) / Decimal(12)).quantize(
        Q2, rounding=ROUND_HALF_UP
    )


def _closing_with_unrecorded_accrual(
    ledger: AnnualLeaveLedger | None,
    emp: Employee,
    as_of: date,
    days_per_year: int,
) -> Decimal:
    """Số dư sổ + phần tích lũy đến `as_of` chưa kịp ghi bút toán — không đụng DB.

    Phải ra đúng con số như sau khi `sync_accrual_batch` đã ghi, nếu lệch thì cột
    «Phép còn» sẽ nhảy số vào lúc chốt kỳ lương.
    """
    target = _target_accrued(emp, as_of, days_per_year)
    if ledger is None:
        return target
    closing = Decimal(str(ledger.closing_balance)).quantize(Q2, rounding=ROUND_HALF_UP)
    missing = (target - Decimal(str(ledger.accrued))).quantize(Q2, rounding=ROUND_HALF_UP)
    if missing <= 0:
        return closing
    return (closing + missing).quantize(Q2, rounding=ROUND_HALF_UP)


def annual_leave_remaining_batch(
    db: Session,
    employee_ids: list[UUID],
    as_of: date | None = None,
) -> dict[UUID, Decimal]:
    """Số phép còn theo lô — CHỈ ĐỌC, 3 query, không INSERT/UPDATE (22§22.7).

    Bút toán tích lũy ghi ở `sync_accrual_batch` (đường lệnh). Không đưa lệnh ghi
    trở lại đây: hàm này chạy trên `GET /api/employees`, mà `get_db()` không commit
    nên mọi INSERT/UPDATE đều bị rollback rồi lặp lại ở request sau.
    """
    if not employee_ids:
        return {}
    as_of = as_of or date.today()
    year = as_of.year
    base, extra_every = _al_policy(db)

    employees = {
        e.id: e for e in db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
    }
    ledger_by_emp = {
        row.employee_id: row
        for row in db.query(AnnualLeaveLedger)
        .filter(
            AnnualLeaveLedger.employee_id.in_(employee_ids),
            AnnualLeaveLedger.year == year,
        )
        .all()
    }
    pending_map = pending_submitted_days_batch(db, employee_ids, year)

    out: dict[UUID, Decimal] = {}
    for emp_id in employee_ids:
        emp = employees.get(emp_id)
        if emp is None:
            out[emp_id] = Decimal("0")
            continue
        closing = _closing_with_unrecorded_accrual(
            ledger_by_emp.get(emp_id),
            emp,
            as_of,
            entitled_days_per_year(emp, as_of, base, extra_every),
        )
        pending = pending_map.get(emp_id, Decimal("0"))
        remaining = (closing - pending).quantize(Q2, rounding=ROUND_HALF_UP)
        out[emp_id] = max(Decimal("0"), remaining)
    return out


def sync_accrual_batch(
    db: Session,
    *,
    employee_ids: list[UUID] | None = None,
    as_of: date | None = None,
) -> int:
    """Ghi bút toán tích lũy phép cho cả lô — ĐƯỜNG LỆNH, trả về số bút toán mới.

    Gọi khi chốt kỳ lương (hoặc job tháng), KHÔNG gọi từ endpoint GET.
    """
    as_of = as_of or date.today()
    year = as_of.year
    base, extra_every = _al_policy(db)

    emp_query = db.query(Employee).filter(Employee.deleted_at.is_(None))
    if employee_ids is not None:
        if not employee_ids:
            return 0
        emp_query = emp_query.filter(Employee.id.in_(employee_ids))
    employees = emp_query.all()
    if not employees:
        return 0

    ids = [e.id for e in employees]
    ledger_by_emp = {
        row.employee_id: row
        for row in db.query(AnnualLeaveLedger)
        .filter(AnnualLeaveLedger.employee_id.in_(ids), AnnualLeaveLedger.year == year)
        .all()
    }
    missing = [emp.id for emp in employees if emp.id not in ledger_by_emp]
    if missing:
        created = [
            AnnualLeaveLedger(
                employee_id=emp_id,
                year=year,
                opening_balance=Decimal("0"),
                accrued=Decimal("0"),
                used=Decimal("0"),
                adjusted=Decimal("0"),
                closing_balance=Decimal("0"),
            )
            for emp_id in missing
        ]
        db.add_all(created)
        db.flush()
        for row in created:
            ledger_by_emp[row.employee_id] = row

    ledger_ids = [led.id for led in ledger_by_emp.values()]
    existing_refs = {
        (led_id, ref)
        for led_id, ref in db.query(
            AnnualLeaveEntry.ledger_id, AnnualLeaveEntry.reference
        ).filter(AnnualLeaveEntry.ledger_id.in_(ledger_ids))
    }

    new_entries: list[AnnualLeaveEntry] = []
    touched: list[AnnualLeaveLedger] = []
    for emp in employees:
        ledger = ledger_by_emp.get(emp.id)
        if ledger is None:
            continue
        months = _accrual_months(emp, as_of)
        if months <= 0:
            continue
        days_per_year = entitled_days_per_year(emp, as_of, base, extra_every)
        delta = (
            _target_accrued(emp, as_of, days_per_year) - Decimal(str(ledger.accrued))
        ).quantize(Q2, rounding=ROUND_HALF_UP)
        if delta <= 0:
            continue
        reference = f"accrual-{year}-through-{months:02d}"
        if (ledger.id, reference) in existing_refs:
            continue
        new_entries.append(
            AnnualLeaveEntry(
                ledger_id=ledger.id,
                entry_date=as_of,
                kind=KIND_ACCRUAL,
                days=delta,
                reference=reference,
                note=f"Tích lũy đến tháng {months}/{year}",
            )
        )
        touched.append(ledger)

    if not new_entries:
        return 0
    db.add_all(new_entries)
    db.flush()
    _refresh_ledger_summary_batch(db, touched)
    return len(new_entries)


def annual_leave_remaining(db: Session, employee_id: UUID, as_of: date | None = None) -> Decimal:
    """Số phép còn = sổ bút toán − đơn ALE đang chờ duyệt."""
    as_of = as_of or date.today()
    return annual_leave_remaining_batch(db, [employee_id], as_of).get(employee_id, Decimal("0"))


def timesheet_ale_used_ytd(db: Session, employee_id: UUID, as_of: date) -> Decimal:
    """Tổng ngày ALE trên bảng công các tháng đã mở trong năm — CHỈ ĐỌC.

    HR gán phép trên lưới ngày (không qua đơn) thì sổ `ledger.used` = 0;
    phiếu công nhân phải lấy số này để hiện «đã dùng» và trừ «còn lại».
    """
    total = (
        db.query(func.coalesce(func.sum(TimesheetMonth.al_days), 0))
        .join(PayPeriod, PayPeriod.id == TimesheetMonth.pay_period_id)
        .filter(
            TimesheetMonth.employee_id == employee_id,
            PayPeriod.year == as_of.year,
            PayPeriod.date_from <= as_of,
        )
        .scalar()
    )
    return Decimal(str(total or 0)).quantize(Q2, rounding=ROUND_HALF_UP)


def annual_leave_snapshot(
    db: Session, employee_id: UUID, as_of: date | None = None
) -> tuple[Decimal, Decimal, Decimal]:
    """(định mức năm, đã dùng, còn lại) — CHỈ ĐỌC, không INSERT/UPDATE sổ.

    Dùng trên GET phiếu lương.
    «Đã dùng» = max(sổ bút toán, tổng ALE bảng công YTD) — lưới ngày cũng trừ.
    «Còn lại» = remaining sổ − phần ALE lưới chưa ghi bút toán.
    """
    as_of = as_of or date.today()
    year = as_of.year
    emp = db.get(Employee, employee_id)
    zero = Decimal("0").quantize(Q2)
    if emp is None:
        return zero, zero, zero
    entitled = Decimal(entitled_days_for(db, emp, as_of)).quantize(Q2, rounding=ROUND_HALF_UP)
    remaining = annual_leave_remaining(db, employee_id, as_of)
    ledger = (
        db.query(AnnualLeaveLedger)
        .filter(
            AnnualLeaveLedger.employee_id == employee_id,
            AnnualLeaveLedger.year == year,
        )
        .one_or_none()
    )
    ledger_used = (
        Decimal(str(ledger.used)).quantize(Q2, rounding=ROUND_HALF_UP) if ledger is not None else zero
    )
    ts_used = timesheet_ale_used_ytd(db, employee_id, as_of)
    used = max(ledger_used, ts_used)
    extra = (used - ledger_used).quantize(Q2, rounding=ROUND_HALF_UP)
    if extra > 0:
        remaining = max(zero, (remaining - extra).quantize(Q2, rounding=ROUND_HALF_UP))
    return entitled, used, remaining


def verify_annual_leave_nghiem_thu_47(
    db: Session,
    *,
    employee_id: UUID,
    as_of: date,
    payslip_remaining: Decimal,
) -> tuple[bool, str]:
    """
    24§ nghiệm thu 4.7 — số phép trên phiếu khớp sổ bút toán.
    closing_balance phải bằng tổng các dòng; phiếu dùng cùng hàm annual_leave_remaining.
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        return False, "Không tìm thấy NV"
    ledger = sync_accrual(db, emp, as_of)
    sum_entries = ledger_balance_from_entries(db, ledger.id)
    closing_ok = ledger.closing_balance.quantize(Q2) == sum_entries.quantize(Q2)
    expected = annual_leave_remaining(db, employee_id, as_of)
    slip_rem = Decimal(str(payslip_remaining)).quantize(Q2, rounding=ROUND_HALF_UP)
    payslip_ok = slip_rem == expected.quantize(Q2)
    ok = closing_ok and payslip_ok
    detail = (
        f"MSNV {emp.employee_code}: sổ={sum_entries} closing={ledger.closing_balance} "
        f"phiếu={slip_rem} kỳ_vọng={expected}"
    )
    if not closing_ok:
        detail += " — lệch sổ/closing"
    if not payslip_ok:
        detail += " — lệch phiếu/hàm"
    return ok, detail
