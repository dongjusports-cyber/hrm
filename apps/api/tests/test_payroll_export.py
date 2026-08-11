"""P5.2 — Xuất Excel ATM / CASH + audit log."""

from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.core.export_log import ExportLog
from app.modules.mdm.models import Employee


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _calc(client, db):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    pay = ensure_pay_period(db, "2025-10")
    for emp in db.query(Employee).filter(Employee.deleted_at.is_(None)).all():
        ts = (
            db.query(TimesheetMonth)
            .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
            .one()
        )
        ts.worked_days = Decimal("26")
    # 1 NV CASH, còn lại ATM có TK
    cash = db.query(Employee).filter(Employee.employee_code == "1732").one()
    cash.pay_channel = "CASH"
    cash.bank_account = None
    atm = db.query(Employee).filter(Employee.employee_code == "5290").one()
    atm.pay_channel = "ATM"
    atm.bank_account = "0123456789"
    db.commit()

    from app.modules.attendance.timesheet import ensure_pay_period as ensure
    from app.modules.payroll import service as payroll_service

    def _noop(db_sess, period, *, recalc_days=True):
        ensure(db_sess, period)
        return type(
            "R",
            (),
            {"rows_upserted": 0, "message": "noop", "period": period, "pay_period_id": pay.id},
        )()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _noop
    try:
        assert (
            client.post(
                "/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client)
            ).status_code
            == 200
        )
    finally:
        payroll_service.rebuild_timesheets = original


def test_export_atm_cash_and_audit(client, db):
    _calc(client, db)

    atm = client.get(
        "/api/payroll/periods/2025-10/export?channel=ATM",
        headers=_hr_headers(client),
    )
    assert atm.status_code == 200, atm.text
    assert "spreadsheetml" in atm.headers["content-type"]
    wb = load_workbook(BytesIO(atm.content))
    assert "ATM" in wb.sheetnames
    sheet = wb["ATM"]
    headers = [c.value for c in sheet[1]]
    assert "Số tài khoản" in headers
    assert "Thực lãnh (VND)" in headers
    # Có ít nhất 1 dòng dữ liệu + header
    assert sheet.max_row >= 2

    cash = client.get(
        "/api/payroll/periods/2025-10/export?channel=CASH",
        headers=_hr_headers(client),
    )
    assert cash.status_code == 200
    wb_c = load_workbook(BytesIO(cash.content))
    assert "CASH" in wb_c.sheetnames
    codes = [wb_c["CASH"].cell(r, 2).value for r in range(2, wb_c["CASH"].max_row + 1)]
    assert "1732" in codes

    both = client.get(
        "/api/payroll/periods/2025-10/export?channel=ALL",
        headers=_hr_headers(client),
    )
    assert both.status_code == 200
    wb_a = load_workbook(BytesIO(both.content))
    assert set(wb_a.sheetnames) >= {"ATM", "CASH", "Tong_hop"}

    logs = db.query(ExportLog).filter(ExportLog.kind.like("payroll_%")).all()
    assert len(logs) >= 3
    assert all(l.period == "2025-10" for l in logs)


def test_export_bad_channel(client, db):
    res = client.get(
        "/api/payroll/periods/2025-10/export?channel=BTC",
        headers=_hr_headers(client),
    )
    assert res.status_code == 400
