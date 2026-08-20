"""P4.5 — Gemini ai_query (stub) + quyền + rà soát dispute."""

from decimal import Decimal

from app.modules.attendance.models import TimesheetMonth
from app.modules.attendance.timesheet import ensure_pay_period, rebuild_timesheets
from app.modules.mdm.models import Employee
from tests.worker_auth import unlocked_worker_headers


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
    return unlocked_worker_headers(client, code)


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
    assert body["stub"] is False
    assert body["model_name"] == "direct"
    assert "5290" in body["answer"]
    assert "Kết quả tra cứu từ hệ thống" in body["answer"]


def test_ai_query_leave_review_direct(client):
    from tests.worker_auth import default_login_password, worker_auth_headers, worker_login_json

    token = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290")),
    ).json()["access_token"]
    created = client.post(
        "/api/worker/leave-requests",
        headers=worker_auth_headers(token, "5290"),
        json={
            "leave_type_code": "OFF",
            "from_date": "2025-11-01",
            "to_date": "2025-11-01",
            "reason": "Nghỉ bù test AI",
            "submit": True,
        },
    )
    assert created.status_code == 200, created.text
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Đơn phép chờ duyệt"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "leave_review"
    assert body["model_name"] == "direct"
    assert "5290" in body["answer"]
    assert "Kết quả đơn phép" in body["answer"]


def test_ai_query_employee_lookup_analysis_uses_stub(client, db):
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Phân tích lương nhân viên 5290"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "employee_lookup"
    assert body["stub"] is True
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


def test_ai_query_dispute_forbidden_without_payroll_or_dispute(client, db):
    """QA-05: chỉ có ai_query + chấm công — không được đọc lương trong khiếu nại."""
    dispute_id = _calc_publish_dispute(client, db)
    created = client.post(
        "/api/users",
        headers=_admin_headers(client),
        json={
            "username": "tk.chamcong",
            "full_name": "Nguyen Cham Cong",
            "password": "ChamCong@123456",
            "modules": ["timekeeping", "overview"],
            "permissions": ["ai_query"],
            "must_change_password": False,
        },
    )
    assert created.status_code == 201, created.text
    token = client.post(
        "/api/auth/login",
        json={"username": "tk.chamcong", "password": "ChamCong@123456"},
    ).json()["access_token"]
    res = client.post(
        "/api/ai/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"dispute_id": dispute_id, "message": ""},
    )
    assert res.status_code == 403, res.text
    assert "không có quyền rà soát khiếu nại" in res.json()["detail"]


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


def test_ai_query_employee_lookup_by_name(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.full_name = "Lê Văn C"
    db.commit()
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Thông tin Lê Văn C"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "employee_lookup"
    assert body["model_name"] == "direct"
    assert "5290" in body["answer"]
    assert "Lê Văn C" in body["answer"]


def test_ai_query_probation_list_direct(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.status = "probation"
    db.commit()
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Nhân viên thử việc"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "probation_list"
    assert body["model_name"] == "direct"
    assert "5290" in body["answer"]


def test_ai_assist_hr_briefing(client):
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "Tóm tắt việc cần làm hôm nay"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "daily_briefing"
    assert body["model_name"] == "direct"


def test_ai_assist_hr_rejects_free_chat(client):
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "Nhà máy có bao nhiêu module Portal?"},
    )
    assert res.status_code == 403
    assert "ai_query" in res.json()["detail"]


def test_ai_assist_hr_name_lookup(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    emp.full_name = "Lê Văn C"
    db.commit()
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "Thông tin Lê Văn C"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "employee_lookup"
    assert "5290" in body["answer"]


def _hrefs(body: dict) -> list[str]:
    return [s.get("href") or "" for s in body.get("suggestions") or []]


def test_ai_assist_open_timesheet_company(client):
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "Mở bảng công cả công ty"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "timesheet_open"
    assert body["model_name"] == "direct"
    assert "bảng công" in body["answer"].lower()
    hrefs = _hrefs(body)
    assert any("/m/timekeeping" in h and "view=monthly" in h for h in hrefs)


def test_ai_assist_print_timesheet_department(client):
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "In bảng công bộ phận SW1 tháng 2026-08"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "timesheet_open"
    hrefs = _hrefs(body)
    assert any("dept=SW1" in h and "/m/timekeeping" in h for h in hrefs)
    assert any("/export" in h and "department_code=SW1" in h for h in hrefs)


def test_ai_assist_timesheet_msnv_not_profile(client):
    res = client.post(
        "/api/ai/assist",
        headers=_hr_headers(client),
        json={"message": "mở bảng công 5290"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "timesheet_open"
    assert "5290" in body["answer"]
    hrefs = _hrefs(body)
    assert any("q=5290" in h for h in hrefs)

