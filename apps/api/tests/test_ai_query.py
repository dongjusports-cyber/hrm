"""P4.5 — Gemini ai_query (stub) + quyền + rà soát dispute."""

from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from app.modules.worker.service import DEFAULT_WORKER_PASSWORD


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


def _worker_headers(client, code="5290"):
    token = client.post(
        "/api/worker/login",
        json={"employee_code": code, "password": DEFAULT_WORKER_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _calc_publish_dispute(client, db) -> str:
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
        client.post("/api/payroll/periods/2025-10/publish", headers=_hr_headers(client)).status_code
        == 200
    )
    slip_id = client.get("/api/worker/payslips", headers=_worker_headers(client)).json()[0]["id"]
    res = client.post(
        f"/api/worker/payslips/{slip_id}/dispute",
        headers=_worker_headers(client),
        json={"reason_code": "wrong_ot", "description": "Thiếu OT Chủ nhật 4 giờ."},
    )
    assert res.status_code == 200, res.text
    return res.json()["id"]


def test_ai_query_requires_permission(client):
    res = client.post(
        "/api/ai/query",
        headers=_hr_headers(client),
        json={"message": "Tóm tắt kỳ lương"},
    )
    assert res.status_code == 403


def test_ai_query_chat_stub(client):
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Nhà máy có bao nhiêu module Portal?"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "chat"
    assert body["stub"] is True
    assert "Trợ Lý AI" in body["answer"]
    assert body["remaining_today"] >= 0


def test_ai_query_employee_lookup_stub(client, db):
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Lấy thông tin nhân viên 5290"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "employee_lookup"
    assert body["stub"] is True
    # Stub nhúng snippet payload — phải có MSNV trong câu trả lời hoặc job prompt
    assert "5290" in body["answer"]


def test_ai_query_dispute_review(client, db):
    dispute_id = _calc_publish_dispute(client, db)
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"dispute_id": dispute_id, "message": ""},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "dispute_review"
    assert body["dispute_code"]
    assert body["stub"] is True

    detail = client.get(f"/api/disputes/{dispute_id}", headers=_hr_headers(client)).json()
    assert detail["status"] == "ai_reviewed"
    assert detail["ai_summary"]


def test_ai_settings_admin(client):
    get_res = client.get("/api/ai/settings", headers=_admin_headers(client))
    assert get_res.status_code == 200
    put = client.put(
        "/api/ai/settings",
        headers=_admin_headers(client),
        json={"enabled": True, "model_name": "gemini-2.0-flash", "max_queries_per_day": 15},
    )
    assert put.status_code == 200, put.text
    assert put.json()["max_queries_per_day"] == 15

    denied = client.get("/api/ai/settings", headers=_hr_headers(client))
    assert denied.status_code == 403
