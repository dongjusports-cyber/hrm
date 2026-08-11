"""4.7 — annual_leave_ledger + bút toán phép năm."""

from datetime import date
from decimal import Decimal

from app.modules.attendance.annual_leave_ledger import (
    annual_leave_remaining,
    ensure_ledger,
    ledger_balance_from_entries,
    record_leave_use,
    sync_accrual,
)
from app.modules.attendance.models import AnnualLeaveEntry, LeaveRequest
from app.modules.mdm.models import Employee


def test_accrual_through_august_matches_22_7(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.join_date = date(2010, 1, 1)
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
    emp.join_date = date(2010, 1, 1)
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


def test_ensure_ledger_idempotent(db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    a = ensure_ledger(db, emp.id, 2025)
    b = ensure_ledger(db, emp.id, 2025)
    assert a.id == b.id
