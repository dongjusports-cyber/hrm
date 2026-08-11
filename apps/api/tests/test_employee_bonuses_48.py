"""4.8 — employee_bonuses + đẩy vào tính lương."""

from decimal import Decimal
from uuid import UUID

from app.modules.payroll.models import EmployeeBonus
from tests.test_oct2025_regression import apply_oct2025_fixture


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_bonus_and_include_in_calculate(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)

    base = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert base.status_code == 200, base.text
    gross0 = Decimal(str(next(s for s in base.json()["payslips"] if s["employee_code"] == "5290")["gross"]))

    created = client.post(
        "/api/payroll/bonuses",
        headers=headers,
        json={
            "employee_code": "5290",
            "bonus_year": 2025,
            "seq_times": 1,
            "bonus_code": "TET",
            "bonus_amount": "500000",
            "period": "2025-10",
            "reason": "Thưởng Tết đợt 1",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert Decimal(str(body["bonus_amount"])) == Decimal("500000")
    assert body["applied_at"] is None

    calc = client.post("/api/payroll/periods/2025-10/calculate", headers=headers)
    assert calc.status_code == 200, calc.text
    slip5290 = next(s for s in calc.json()["payslips"] if s["employee_code"] == "5290")
    assert Decimal(str(slip5290["gross"])) == gross0 + Decimal("500000")

    comps = client.get(
        f"/api/payroll/payslips/{slip5290['id']}/components",
        headers=headers,
    ).json()
    bonus_lines = [c for c in comps if c["component_code"] == "BONUS"]
    assert len(bonus_lines) == 1
    assert Decimal(str(bonus_lines[0]["amount"])) == Decimal("500000")

    row = db.query(EmployeeBonus).filter(EmployeeBonus.id == UUID(body["id"])).one()
    assert row.applied_at is not None


def test_two_bonus_installments_same_year(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    for seq, period, amount in ((1, "2025-10", "300000"), (2, "2025-11", "200000")):
        res = client.post(
            "/api/payroll/bonuses",
            headers=headers,
            json={
                "employee_code": "5290",
                "bonus_year": 2025,
                "seq_times": seq,
                "bonus_amount": amount,
                "period": period,
            },
        )
        assert res.status_code == 201, res.text

    rows = (
        db.query(EmployeeBonus)
        .filter(EmployeeBonus.bonus_year == 2025)
        .order_by(EmployeeBonus.seq_times)
        .all()
    )
    assert len(rows) == 2
    assert int(rows[0].seq_times) == 1
    assert int(rows[1].seq_times) == 2


def test_duplicate_bonus_rejected(client, db):
    apply_oct2025_fixture(db)
    headers = _hr_headers(client)
    payload = {
        "employee_code": "5290",
        "bonus_year": 2025,
        "seq_times": 9,
        "bonus_amount": "100000",
        "period": "2025-10",
    }
    assert client.post("/api/payroll/bonuses", headers=headers, json=payload).status_code == 201
    dup = client.post("/api/payroll/bonuses", headers=headers, json=payload)
    assert dup.status_code == 400
