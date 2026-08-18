"""P4.1 — Worker xem phiếu lương đã phát hành."""

from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.payroll.models import Payslip
from tests.worker_auth import unlocked_worker_headers


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _worker_headers(client, code="5290"):
    return unlocked_worker_headers(client, code)


def _calc_and_publish(client, db, code="5290"):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    pay = ensure_pay_period(db, "2025-10")
    emp = db.query(Employee).filter(Employee.employee_code == code).one()
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("27")
    db.commit()

    from app.modules.attendance.timesheet import ensure_pay_period as ensure
    from app.modules.payroll import service as payroll_service

    def _noop(db_sess, period, *, recalc_days=True):
        ensure(db_sess, period)
        return type("R", (), {"rows_upserted": 0, "message": "noop", "period": period, "pay_period_id": pay.id})()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _noop
    try:
        assert client.post(
            "/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client)
        ).status_code == 200
    finally:
        payroll_service.rebuild_timesheets = original

    pub = client.post("/api/payroll/periods/2025-10/publish", headers=_hr_headers(client))
    assert pub.status_code == 200, pub.text


def test_worker_sees_only_published(client, db):
    # Trước phát hành: danh sách rỗng
    empty = client.get("/api/worker/payslips", headers=_worker_headers(client))
    assert empty.status_code == 200
    assert empty.json() == []

    _calc_and_publish(client, db)

    # Draft không còn — đã published
    listed = client.get("/api/worker/payslips", headers=_worker_headers(client))
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) >= 1
    assert body[0]["period"] == "2025-10"
    assert body[0]["status"] == "published"
    assert Decimal(str(body[0]["net"])) > 0

    detail = client.get(
        f"/api/worker/payslips/{body[0]['id']}",
        headers=_worker_headers(client),
    )
    assert detail.status_code == 200
    d = detail.json()
    assert d["can_confirm"] is True
    assert d["can_dispute"] is True
    assert isinstance(d["work_lines"], list)
    assert isinstance(d["leave_lines"], list)
    assert isinstance(d["allowance_lines"], list)
    assert isinstance(d["deduction_lines"], list)
    assert len(d["work_lines"]) >= 1
    assert len(d["deduction_lines"]) >= 1
    assert len(d["allowance_lines"]) == 11
    assert len(d["work_lines"]) == 5
    assert d["employee_code"] == "5290"
    assert "taxable_income" in d
    assert d["annual_leave_entitled"] is not None
    assert Decimal(str(d["annual_leave_entitled"])) > 0
    assert d["annual_leave_current"] is not None
    assert Decimal(str(d["annual_leave_current"])) > 0
    assert Decimal(str(d["annual_leave_current"])) <= Decimal(str(d["annual_leave_entitled"]))
    assert d["annual_leave_used"] is not None
    assert d["annual_leave_remaining"] is not None
    assert Decimal(str(d["annual_leave_remaining"])) == (
        Decimal(str(d["annual_leave_current"])) - Decimal(str(d["annual_leave_used"]))
    )
    assert all(ln.get("label") != "Thuế TNCN" for ln in d["deduction_lines"])

    from uuid import UUID

    from app.modules.payroll.payslip_detail import get_hr_payslip_detail

    hr = get_hr_payslip_detail(db, UUID(body[0]["id"]))
    assert float(d["net"]) == float(hr.payslip.net)
    hr_work = sum(Decimal(str(x.amount)) for x in hr.work_lines)
    hr_allow = sum(Decimal(str(x.amount)) for x in hr.allowance_lines)
    w_work = sum(
        Decimal(str(x["amount"])) for x in d["work_lines"] if x.get("amount") is not None
    )
    w_leave = sum(
        Decimal(str(x["amount"])) for x in d["leave_lines"] if x.get("amount") is not None
    )
    w_allow = sum(
        Decimal(str(x["amount"])) for x in d["allowance_lines"] if x.get("amount") is not None
    )
    assert w_work + w_leave == hr_work
    assert w_allow == hr_allow


def test_worker_cannot_see_other_employee_payslip(client, db):
    _calc_and_publish(client, db, code="5290")
    slip = (
        db.query(Payslip)
        .join(Employee)
        .filter(Employee.employee_code == "5290", Payslip.status == "published")
        .first()
    )
    assert slip is not None

    # Worker khác
    res = client.get(
        f"/api/worker/payslips/{slip.id}",
        headers=_worker_headers(client, "1514"),
    )
    assert res.status_code == 404


def test_draft_hidden_from_worker(client, db):
    ensure_pay_period(db, "2025-10")
    rebuild_timesheets(db, "2025-10", recalc_days=False)
    pay = ensure_pay_period(db, "2025-10")
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    ts = (
        db.query(TimesheetMonth)
        .filter(TimesheetMonth.pay_period_id == pay.id, TimesheetMonth.employee_id == emp.id)
        .one()
    )
    ts.worked_days = Decimal("27")
    db.commit()

    from app.modules.attendance.timesheet import ensure_pay_period as ensure
    from app.modules.payroll import service as payroll_service

    def _noop(db_sess, period, *, recalc_days=True):
        ensure(db_sess, period)
        return type("R", (), {"rows_upserted": 0, "message": "noop", "period": period, "pay_period_id": pay.id})()

    original = payroll_service.rebuild_timesheets
    payroll_service.rebuild_timesheets = _noop
    try:
        client.post("/api/payroll/periods/2025-10/calculate", headers=_hr_headers(client))
    finally:
        payroll_service.rebuild_timesheets = original

    listed = client.get("/api/worker/payslips", headers=_worker_headers(client))
    assert listed.json() == []


def test_worker_payslip_shows_grid_ale_quantity_and_used(client, db):
    """Gán ALE trên lưới ngày → section II có số ngày, section V có đã dùng."""
    headers = _hr_headers(client)
    patch = client.patch(
        "/api/attendance/days/cell",
        headers=headers,
        json={"employee_code": "5290", "work_date": "2025-10-06", "leave_code": "ALE"},
    )
    assert patch.status_code == 200, patch.text

    _calc_and_publish(client, db, code="5290")

    listed = client.get("/api/worker/payslips", headers=_worker_headers(client))
    assert listed.status_code == 200
    body = listed.json()
    assert body
    detail = client.get(
        f"/api/worker/payslips/{body[0]['id']}",
        headers=_worker_headers(client),
    )
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert Decimal(str(d["al_days"])) >= 1
    ale = next(ln for ln in d["leave_lines"] if ln["label"] == "Nghỉ phép năm")
    assert Decimal(str(ale["quantity"])) == Decimal(str(d["al_days"]))
    assert ale["amount"] is not None
    assert Decimal(str(ale["amount"])) > 0
    assert Decimal(str(d["annual_leave_used"])) >= Decimal(str(d["al_days"]))
    assert Decimal(str(d["annual_leave_entitled"])) > 0
    assert Decimal(str(d["annual_leave_current"])) > 0
    assert Decimal(str(d["annual_leave_remaining"])) == (
        Decimal(str(d["annual_leave_current"])) - Decimal(str(d["annual_leave_used"]))
    )
    assert all(ln.get("label") != "Thuế TNCN" for ln in d["deduction_lines"])
