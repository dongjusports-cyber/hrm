"""5.7 — todo cards on /ai/todos and overview."""

from datetime import datetime, timedelta

from app.modules.attendance.engine import VN_TZ
from app.modules.mdm.models import Employee, EmployeeWtRegime, LabourContract


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _vn_today():
    return datetime.now(tz=VN_TZ).date()


def test_todos_include_expiring_contracts(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    today = _vn_today()
    db.add(
        LabourContract(
            employee_id=emp.id,
            contract_type_code="HD1",
            start_date=today - timedelta(days=200),
            end_date=today + timedelta(days=20),
            base_salary=8335000,
            status="active",
        )
    )
    db.commit()

    res = client.get("/api/ai/todos", headers=headers)
    assert res.status_code == 200
    keys = {c["key"] for c in res.json()["cards"]}
    assert "expiring_contracts_60d" in keys


def test_todos_include_wt_regime_expiring(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    today = _vn_today()
    db.add(
        EmployeeWtRegime(
            employee_id=emp.id,
            regime_type="CHILD",
            hours_early=2,
            date_from=today,
            date_to=today + timedelta(days=3),
            note="test",
        )
    )
    db.commit()

    res = client.get("/api/ai/todos", headers=headers)
    assert res.status_code == 200
    keys = {c["key"] for c in res.json()["cards"]}
    assert "wt_regime_expiring" in keys


def test_overview_includes_todo_cards(client, db):
    headers = _hr_headers(client)
    today = _vn_today()
    period = f"{today.year:04d}-{today.month:02d}"
    res = client.get("/api/reports/overview", headers=headers, params={"period": period})
    assert res.status_code == 200
    assert "todo_cards" in res.json()


def test_overview_ok_when_todo_cards_nonempty(client, db):
    """QA-02 / REP-OV001: HĐ sắp hết hạn → overview 200, không 500 vì TodoCardOut trùng."""
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    today = _vn_today()
    db.add(
        LabourContract(
            employee_id=emp.id,
            contract_type_code="HD1",
            start_date=today - timedelta(days=200),
            end_date=today + timedelta(days=20),
            base_salary=8335000,
            status="active",
        )
    )
    db.commit()
    period = f"{today.year:04d}-{today.month:02d}"
    res = client.get("/api/reports/overview", headers=headers, params={"period": period})
    assert res.status_code == 200, res.text
    cards = res.json()["todo_cards"]
    assert len(cards) >= 1
    assert any(c["key"] == "expiring_contracts_60d" for c in cards)


def test_todos_include_pending_leave_requests(client):
    from tests.worker_auth import default_login_password, worker_auth_headers, worker_login_json

    token = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290")),
    ).json()["access_token"]
    worker = worker_auth_headers(token, "5290")
    created = client.post(
        "/api/worker/leave-requests",
        headers=worker,
        json={
            "leave_type_code": "ALE",
            "from_date": "2025-10-20",
            "to_date": "2025-10-20",
            "reason": "Test todo phép",
            "submit": True,
        },
    )
    assert created.status_code == 200, created.text

    res = client.get("/api/ai/todos", headers=_hr_headers(client))
    assert res.status_code == 200
    card = next(c for c in res.json()["cards"] if c["key"] == "leave_requests_pending")
    assert card["count"] >= 1
    assert card["href"] == "/m/timekeeping?view=leave"
    assert card.get("ask_message")
