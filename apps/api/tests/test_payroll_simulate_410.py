"""4.10 — Chạy thử lương không ghi CSDL."""

from copy import deepcopy
from datetime import date
from decimal import Decimal

from app.modules.mdm.models import Employee
from app.modules.payroll.models import PayrollRun, Payslip
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload
from tests.test_oct2025_regression import apply_oct2025_fixture


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_simulate_policy_options(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    res = client.get("/api/payroll/simulate/policy-options", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) >= 1
    assert "id" in body[0] and "name" in body[0]


def test_simulate_does_not_write_db(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    assert client.post("/api/payroll/periods/2025-10/calculate", headers=headers).status_code == 200

    emp = db.query(Employee).filter(Employee.employee_code == "5290").one()
    slip5290 = db.query(Payslip).filter(Payslip.employee_id == emp.id).one()
    net_before = Decimal(str(slip5290.net))
    runs_before = db.query(PayrollRun).count()

    alt = PolicyPackage(
        name="Chạy thử 650k chuyên cần",
        effective_from=date(2025, 1, 1),
        is_active=False,
        version=1,
        payload=deepcopy(default_payload()),
    )
    alt.payload["attendance_bonus_monthly"] = 650_000
    db.add(alt)
    db.commit()
    db.refresh(alt)

    sim = client.post(
        "/api/payroll/simulate",
        headers=headers,
        json={
            "period": "2025-10",
            "policy_package_id": str(alt.id),
            "scope": "employees",
            "employee_codes": ["5290"],
        },
    )
    assert sim.status_code == 200, sim.text
    row = sim.json()["rows"][0]
    assert Decimal(str(row["delta_net"])) != 0
    assert Decimal(str(row["current"]["net"])) == net_before

    db.refresh(slip5290)
    assert Decimal(str(slip5290.net)) == net_before
    assert db.query(PayrollRun).count() == runs_before


def test_simulate_same_policy_zero_delta(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    assert client.post("/api/payroll/periods/2025-10/calculate", headers=headers).status_code == 200

    active = db.query(PolicyPackage).filter(PolicyPackage.is_active.is_(True)).first()
    assert active is not None

    sim = client.post(
        "/api/payroll/simulate",
        headers=headers,
        json={
            "period": "2025-10",
            "policy_package_id": str(active.id),
            "scope": "employees",
            "employee_codes": ["5290"],
        },
    )
    assert sim.status_code == 200, sim.text
    row = sim.json()["rows"][0]
    assert Decimal(str(row["delta_net"])) == 0
