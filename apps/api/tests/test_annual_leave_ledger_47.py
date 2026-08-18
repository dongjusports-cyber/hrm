"""4.7 — annual_leave_ledger + bút toán phép năm."""

from datetime import date
from decimal import Decimal

from app.modules.attendance.annual_leave_ledger import (
    annual_leave_remaining,
    annual_leave_remaining_batch,
    annual_leave_snapshot,
    closed_accrual_months,
    ensure_ledger,
    entitled_days_per_year,
    ledger_balance_from_entries,
    prorate_al,
    record_leave_use,
    sync_accrual,
)
from app.modules.attendance.models import (
    AnnualLeaveEntry,
    AnnualLeaveLedger,
    LeaveRequest,
    TimesheetMonth,
)
from app.modules.mdm.models import Employee


def test_entitled_14_plus_1_per_5_years():
    """1519 vào 26/03/2015: đúng kỷ niệm 5 năm mới +1, không cộng từ đầu năm."""
    emp = Employee(employee_code="1519", full_name="X", join_date=date(2015, 3, 26))
    assert entitled_days_per_year(emp, date(2020, 3, 25), 14, 5) == 14
    assert entitled_days_per_year(emp, date(2020, 3, 26), 14, 5) == 15
    assert entitled_days_per_year(emp, date(2025, 3, 25), 14, 5) == 15
    assert entitled_days_per_year(emp, date(2025, 3, 26), 14, 5) == 16
    assert entitled_days_per_year(emp, date(2026, 8, 17), 14, 5) == 16
    newbie = Employee(employee_code="x", full_name="Y", join_date=date(2026, 1, 10))
    assert entitled_days_per_year(newbie, date(2026, 8, 17), 14, 5) == 14


def test_1519_current_in_august_is_prorated_not_full_quota():
    """1519 được hưởng 16 cả năm; giữa T8 chỉ hiện phép đã tích (hết T7)."""
    emp = Employee(employee_code="1519", full_name="X", join_date=date(2015, 3, 26))
    as_of = date(2026, 8, 18)
    assert entitled_days_per_year(emp, as_of, 14, 5) == 16
    months = closed_accrual_months(emp.join_date, as_of, 2026)
    assert months == 7
    current = prorate_al(Decimal("16"), months)
    assert current == Decimal("9.33")
    used = Decimal("5.00")
    remaining = (current - used).quantize(Decimal("0.01"))
    assert remaining == Decimal("4.33")
    assert remaining != used
    assert current != Decimal("16")
    assert closed_accrual_months(emp.join_date, date(2026, 8, 31), 2026) == 8
    assert prorate_al(Decimal("16"), 8) == Decimal("10.67")


def test_closed_months_ignore_maternity_leave():
    """Nghỉ thai sản tháng 4–10: hết T7 vẫn 7 tháng tích, không bị trừ."""
    join = date(2015, 3, 26)
    as_of = date(2026, 8, 18)
    assert closed_accrual_months(join, as_of, 2026) == 7
    assert prorate_al(Decimal("16"), 7) == Decimal("9.33")



def test_accrual_through_august_matches_22_7(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2024, 1, 1)
    db.commit()

    as_of = date(2025, 8, 31)
    ledger = sync_accrual(db, emp, as_of)
    db.commit()

    assert float(ledger.accrued) == 9.33
    assert float(ledger.closing_balance) == 9.33
    assert float(ledger_balance_from_entries(db, ledger.id)) == float(ledger.closing_balance)


def test_balance_equals_sum_of_entries(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    ledger = sync_accrual(db, emp, date(2025, 8, 31))
    record_leave_use(
        db,
        employee_id=emp.id,
        leave_request_id=emp.id,
        days=Decimal("1.00"),
        entry_date=date(2025, 8, 15),
    )
    db.commit()
    db.refresh(ledger)

    entries = db.query(AnnualLeaveEntry).filter(AnnualLeaveEntry.ledger_id == ledger.id).all()
    movement = sum(
        (e.days if e.kind == "accrual" else -e.days if e.kind in ("use", "payout") else e.days)
        for e in entries
    )
    assert float(ledger.opening_balance + movement) == float(ledger.closing_balance)


def test_remaining_subtracts_pending_submitted(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2024, 1, 1)
    db.commit()

    sync_accrual(db, emp, date(2025, 8, 31))
    req = LeaveRequest(
        employee_id=emp.id,
        leave_type_code="ALE",
        from_date=date(2025, 10, 20),
        to_date=date(2025, 10, 21),
        total_days=Decimal("2.00"),
        reason="test",
        status="submitted",
    )
    db.add(req)
    db.commit()

    remaining = annual_leave_remaining(db, emp.id, date(2025, 8, 31))
    assert float(remaining) == 7.33


def test_remaining_batch_matches_single(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2024, 1, 1)
    db.commit()

    as_of = date(2025, 8, 31)
    sync_accrual(db, emp, as_of)
    db.commit()

    single = annual_leave_remaining(db, emp.id, as_of)
    batch = annual_leave_remaining_batch(db, [emp.id], as_of).get(emp.id)
    assert batch == single


def test_ensure_ledger_idempotent(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    a = ensure_ledger(db, emp.id, 2025)
    b = ensure_ledger(db, emp.id, 2025)
    assert a.id == b.id


def test_snapshot_read_only_and_used_after_leave(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2024, 1, 1)
    db.commit()
    as_of = date(2025, 8, 31)

    before = (
        db.query(AnnualLeaveLedger)
        .filter(AnnualLeaveLedger.employee_id == emp.id, AnnualLeaveLedger.year == 2025)
        .count()
    )
    entitled, current, used, remaining = annual_leave_snapshot(db, emp.id, as_of)
    after = (
        db.query(AnnualLeaveLedger)
        .filter(AnnualLeaveLedger.employee_id == emp.id, AnnualLeaveLedger.year == 2025)
        .count()
    )
    assert after == before
    assert entitled > 0
    assert current > 0
    assert current <= entitled
    assert used >= 0
    assert remaining == current - used

    sync_accrual(db, emp, as_of)
    record_leave_use(
        db,
        employee_id=emp.id,
        leave_request_id=emp.id,
        days=Decimal("2.00"),
        entry_date=date(2025, 8, 10),
    )
    db.commit()
    entitled2, current2, used2, remaining2 = annual_leave_snapshot(db, emp.id, as_of)
    assert used2 == used + Decimal("2.00")
    assert remaining2 == remaining - Decimal("2.00")
    assert remaining2 == current2 - used2
    assert entitled2 == entitled
    assert current2 == current


def test_snapshot_used_includes_timesheet_grid_ale(db):
    """HR gán ALE trên lưới → phiếu phải hiện đã dùng, không chờ duyệt đơn."""
    from app.modules.attendance.timesheet import ensure_pay_period

    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    as_of = date(2025, 10, 31)
    _, _, used_before, rem_before = annual_leave_snapshot(db, emp.id, as_of)

    pay = ensure_pay_period(db, "2025-10")
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one_or_none()
    )
    if ts is None:
        ts = TimesheetMonth(pay_period_id=pay.id, employee_id=emp.id, al_days=Decimal("0"))
        db.add(ts)
        db.flush()
    ts.al_days = Decimal(str(ts.al_days or 0)) + Decimal("2.00")
    db.commit()

    entitled, current, used_after, rem_after = annual_leave_snapshot(db, emp.id, as_of)
    assert used_after == used_before + Decimal("2.00")
    assert rem_after == rem_before - Decimal("2.00")
    assert rem_after == current - used_after
    assert current <= entitled


def test_snapshot_1519_august_shows_current_not_full_year(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2015, 3, 26)
    db.commit()
    as_of = date(2026, 8, 18)
    snap = annual_leave_snapshot(db, emp.id, as_of)
    assert snap.entitled == Decimal("16.00")
    assert snap.current == Decimal("9.33")
    assert snap.remaining == snap.current - snap.used
    assert snap.current != snap.entitled
