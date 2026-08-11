"""P5.3 — Hộp đen audit + export log."""

from app.modules.audit.models import AuditLog
from app.modules.audit.service import write_audit
from app.modules.core.models import User


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_blackbox_admin_only(client, db):
    denied = client.get("/api/audit/blackbox", headers=_hr_headers(client))
    assert denied.status_code == 403

    admin = db.query(User).filter(User.username == "admin").one()
    write_audit(
        db,
        actor=admin,
        action="test.ping",
        entity_type="system",
        entity_id="1",
        summary="Kiểm tra hộp đen",
        meta={"password": "SECRET", "ok": True, "net": 999},
    )
    row = db.query(AuditLog).filter(AuditLog.action == "test.ping").one()
    assert row.meta_json is not None
    assert "password" not in row.meta_json
    assert "net" not in row.meta_json
    assert row.meta_json.get("ok") is True

    res = client.get("/api/audit/blackbox", headers=_admin_headers(client))
    assert res.status_code == 200, res.text
    body = res.json()
    assert "actions" in body and "exports" in body
    assert any(a["action"] == "test.ping" for a in body["actions"])


def test_payroll_actions_write_audit(client, db):
    # Tính lương (noop timesheet) sẽ ghi audit
    from decimal import Decimal

    from app.modules.attendance.models import TimesheetMonth
    from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
    from app.modules.mdm.models import Employee

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

    assert (
        db.query(AuditLog).filter(AuditLog.action == "payroll.calculate").count() >= 1
    )
