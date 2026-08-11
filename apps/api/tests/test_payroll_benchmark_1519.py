"""22§22.11 + 24§ đợt 4 — bài kiểm chứng MSNV 1519 kỳ 07/2026."""

from datetime import date
from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth, TimesheetMonthDetail
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Department, Employee, Team


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _ensure_employee_1519(db) -> Employee:
    existing = db.query(Employee).filter(Employee.employee_code == "1519").one_or_none()
    if existing:
        existing.contract_salary = Decimal("8335000")
        existing.probation_salary = Decimal("8335000")
        existing.join_date = date(2015, 3, 15)
        existing.contract_signed_at = date(2015, 6, 15)
        existing.status = "active"
        existing.si_enrolled = True
        db.commit()
        return existing

    dept = db.query(Department).filter(Department.code == "B01").one()
    team = db.query(Team).filter(Team.department_id == dept.id, Team.code == "T1").one()
    emp = Employee(
        employee_code="1519",
        full_name="Nguyễn Benchmark 1519",
        gender="M",
        pay_channel="ATM",
        team_id=team.id,
        position_title="Nhân viên",
        join_date=date(2015, 3, 15),
        contract_signed_at=date(2015, 6, 15),
        probation_salary=Decimal("8335000"),
        contract_salary=Decimal("8335000"),
        status="active",
        si_enrolled=True,
    )
    db.add(emp)
    db.commit()
    return emp


def test_msnv_1519_july_2026_matches_genussuite(client, db):
    """Thực lãnh phải ra đúng 9.682.398 — không khớp một đồng cũng chưa đạt."""
    emp = _ensure_employee_1519(db)
    pay = ensure_pay_period(db, "2026-07")
    rebuild_timesheets(db, "2026-07", recalc_days=False)

    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("26")
    ts.al_days = Decimal("1")
    ts.ot_hours_weekday = Decimal("0")
    ts.ot_hours_weekend = Decimal("0")
    ts.ot_hours_holiday = Decimal("0")
    db.add(
        TimesheetMonthDetail(
            timesheet_month_id=ts.id,
            category="ABS_ALE",
            segment="official",
            days=Decimal("1"),
        )
    )
    db.commit()

    from app.modules.payroll import service as payroll_service

    original = payroll_service.rebuild_timesheets

    def _rebuild_noop(db_sess, period, *, recalc_days=True):
        ensure_pay_period(db_sess, period)
        return type(
            "R",
            (),
            {
                "rows_upserted": 1,
                "message": "noop",
                "period": period,
                "pay_period_id": pay.id,
            },
        )()

    payroll_service.rebuild_timesheets = _rebuild_noop
    try:
        res = client.post(
            "/api/payroll/periods/2026-07/calculate",
            headers=_hr_headers(client),
        )
    finally:
        payroll_service.rebuild_timesheets = original

    assert res.status_code == 200, res.text
    row = next(p for p in res.json()["payslips"] if p["employee_code"] == "1519")

    assert Decimal(str(row["wd_salary"])) == Decimal("8335000")
    assert Decimal(str(row["allowance_total"])) == Decimal("2003846")
    assert Decimal(str(row["gross"])) == Decimal("10659423")
    assert Decimal(str(row["bhxh"])) == Decimal("710800")
    assert Decimal(str(row["bhyt"])) == Decimal("133275")
    assert Decimal(str(row["bhtn"])) == Decimal("88850")
    assert Decimal(str(row["union_fee"])) == Decimal("44100")
    assert Decimal(str(row["pit_amount"])) == Decimal("0")
    assert Decimal(str(row["net"])) == Decimal("9682398")

    lines = row["lines"]
    assert Decimal(str(lines["leave_pay"]["leave_pay_total"])) == Decimal("320577")
    assert Decimal(str(lines["si_contribution_base"])) == Decimal("8885000")

    by_code = {ln["code"]: Decimal(str(ln["amount"])) for ln in lines["allowances"]["items"]}
    assert by_code["ATTEND"] == Decimal("623077")
    assert by_code["TRANSPORT"] == Decimal("830769")
    assert by_code["SENIORITY"] == Decimal("550000")
