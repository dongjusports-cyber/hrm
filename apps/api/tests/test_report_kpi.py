"""P5.1 — KPI Attendance / OT / Turnover."""

from decimal import Decimal

from app.modules.mdm.models import Employee
from app.modules.report.engine import (
    attendance_rate,
    end_headcount,
    monthly_manpower,
    ot_rate,
    turnover_rate,
)


def test_kpi_engine_formulas():
    assert monthly_manpower(100, Decimal("26")) == Decimal("2600")
    assert attendance_rate(Decimal("2340"), Decimal("2600")) == Decimal("0.9000")
    assert end_headcount(100, 5, 3) == 102
    assert turnover_rate(3, 100, 102) == Decimal("0.0297")
    assert ot_rate(Decimal("200"), Decimal("8000")) == Decimal("0.0250")
    assert attendance_rate(Decimal("1"), Decimal("0")) is None


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_kpi_api_period(client, db):
    # Gán resign trong kỳ để có turnover > 0
    emp = db.query(Employee).filter(Employee.employee_code == "1732").one()
    from datetime import date

    emp.resign_date = date(2025, 10, 20)
    emp.status = "resigned"
    db.commit()

    headers = _hr_headers(client)
    client.post(
        "/api/attendance/timesheets/rebuild",
        headers=headers,
        params={"period": "2025-10"},
    )

    res = client.get("/api/reports/kpi?period=2025-10", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period"] == "2025-10"
    assert body["headcount"] >= 4
    assert body["resign"] >= 1
    assert body["turnover_rate"] is not None
    assert len(body["by_category"]) == 3
    assert any(c["category"] == "direct" for c in body["by_category"])

    ov = client.get("/api/reports/overview?period=2025-10", headers=headers)
    assert ov.status_code == 200
    assert "total_employees" in ov.json()
    assert "open_disputes" in ov.json()

    xlsx = client.get("/api/reports/kpi/export?period=2025-10", headers=headers)
    assert xlsx.status_code == 200
    assert (
        xlsx.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(xlsx.content) > 100
    cd = xlsx.headers.get("content-disposition", "")
    assert "10.2025" in cd
    assert "Dongju" in cd
