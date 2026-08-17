"""4.7 — annual_leave_ledger + bút toán phép năm."""

from datetime import date
from decimal import Decimal

from app.modules.attendance.annual_leave_ledger import (
    annual_leave_remaining,
    annual_leave_remaining_batch,
    ensure_ledger,
    entitled_days_per_year,
    ledger_balance_from_entries,
    record_leave_use,
    sync_accrual,
)
from app.modules.attendance.models import AnnualLeaveEntry, LeaveRequest
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
