"""5.7 — todo cards on /ai/todos and overview."""

from datetime import date, timedelta

from app.modules.mdm.models import Employee, EmployeeWtRegime, LabourContract


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_todos_include_expiring_contracts(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    today = date.today()
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
    today = date.today()
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
    period = f"{date.today().year:04d}-{date.today().month:02d}"
    res = client.get("/api/reports/overview", headers=headers, params={"period": period})
    assert res.status_code == 200
    assert "todo_cards" in res.json()
