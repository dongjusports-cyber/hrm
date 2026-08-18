"""P3.1 — API calculate period → payslip wd_salary."""

from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_calculate_wd_for_fixture_employee(client, db):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)

    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    pay = ensure_pay_period(db, "2025-10")
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    # Neo Excel: đủ tháng 27 công + 27h OT thường
    ts.worked_days = Decimal("27")
    ts.al_days = Decimal("0")
    ts.ot_hours_weekday = Decimal("27")
    db.commit()

    # calculate sẽ rebuild timesheet từ punch (có thể về 0) — tạm patch:
    # gọi engine qua API sau khi stub rebuild bỏ qua bằng cách set lại trong hook?
    # Cách ổn: không recalc — sửa service? Thay vì vậy: inject worked sau calculate
    # không được. Tốt hơn: monkeypatch rebuild trong test.

    from app.modules.payroll import service as payroll_service

    def _rebuild_noop(db_sess, period, *, recalc_days=True):
        ensure_pay_period(db_sess, period)
        # giữ worked_days đã gán
        return type("R", (), {"rows_upserted": 1, "message": "noop", "period": period, "pay_period_id": pay.id})()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _rebuild_noop
    try:
        res = client.post("/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client))
    finally:
        payroll_service.rebuild_timesheets = original

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["run"]["status"] == "success"
    row = next(p for p in body["payslips"] if p["employee_code"] == "5290")
    assert Decimal(str(row["wd_salary"])) == Decimal("5893269")
    assert Decimal(str(row["salary_divisor"])) == Decimal("26")
    # P3.2: ATTEND+TRANSPORT+TOXIC(+SENIORITY) > 0
    assert Decimal(str(row["allowance_total"])) > 0
    assert Decimal(str(row["ot_pay"])) > 0
    assert Decimal(str(row["gross"])) == Decimal(str(row["wd_salary"])) + Decimal(
        str(row["allowance_total"])
    ) + Decimal(str(row["ot_pay"]))
    assert Decimal(str(row["bhxh"])) > 0
    assert Decimal(str(row["union_fee"])) == Decimal("44100")
    assert Decimal(str(row["net"])) == Decimal(str(row["gross"])) - Decimal(str(row["bhxh"])) - Decimal(
        str(row["bhyt"])
    ) - Decimal(str(row["bhtn"])) - Decimal(str(row["union_fee"]))
    assert row["lines"]["phase"].startswith("P4.")
    assert "insurance" in row["lines"]
    assert "adjustments" in row["lines"]

    listed = client.get(
        "/api/payroll/payslips",
        headers=_hr_headers(client),
        params={"period": "2025-10"},
    )
    assert listed.status_code == 200
    assert any(p["employee_code"] == "5290" for p in listed.json())


def test_calculate_rejects_when_run_already_running(client, db):
    """QA-06: đang tính lương thì bấm lại → 409, không chạy song song."""
    from datetime import datetime, timezone

    from app.modules.attendance.timesheet import ensure_pay_period
    from app.modules.payroll.models import PayrollRun

    pay = ensure_pay_period(db, "2025-10")
    db.add(
        PayrollRun(
            pay_period_id=pay.id,
            status="running",
            started_at=datetime.now(timezone.utc),
            message="Đang tính…",
        )
    )
    db.commit()
    res = client.post("/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client))
    assert res.status_code == 409
    assert "đang tính lương" in res.json()["detail"].lower()


def test_only_one_running_payroll_run_per_period(db):
    """Unique index: hai run `running` cùng kỳ → IntegrityError (lớp chặn DB)."""
    from sqlalchemy.exc import IntegrityError

    from app.modules.payroll.models import PayrollRun

    pay = ensure_pay_period(db, "2025-10")
    db.add(PayrollRun(pay_period_id=pay.id, status="running", message="lần 1"))
    db.commit()
    db.add(PayrollRun(pay_period_id=pay.id, status="success", message="đã xong khác"))
    db.commit()
    db.add(PayrollRun(pay_period_id=pay.id, status="running", message="lần 2"))
    try:
        db.commit()
        raise AssertionError("expected IntegrityError")
    except IntegrityError:
        db.rollback()
