"""Bước F — AI nhắc chế độ về sớm T−3 (22§22.14)."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.modules.attendance.engine import VN_TZ
from app.modules.mdm.models import Employee, EmployeeWtRegime


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _vn_today():
    return datetime.now(tz=VN_TZ).date()


def _add_regime(db, emp: Employee, *, date_to, regime_type: str = "CHILD") -> EmployeeWtRegime:
    today = _vn_today()
    r = EmployeeWtRegime(
        id=uuid4(),
        employee_id=emp.id,
        regime_type=regime_type,
        hours_early=2 if regime_type == "CHILD" else 1,
        date_from=today,
        date_to=date_to,
        note="test",
    )
    db.add(r)
    db.commit()
    return r


def _wt_alerts(payload: dict) -> list[dict]:
    return [a for a in payload["alerts"] if a["rule_key"] == "wt_regime_expiring"]


def test_wt_regime_alert_on_t_minus_3(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    target = _vn_today() + timedelta(days=3)
    _add_regime(db, emp, date_to=target)

    res = client.get("/api/ai/alerts/mine", headers=headers)
    assert res.status_code == 200
    alerts = _wt_alerts(res.json())
    assert len(alerts) == 1
    assert "1514" in alerts[0]["body"]
    assert "Nuôi con nhỏ (2h)" in alerts[0]["body"]
    assert target.strftime("%d/%m/%Y") in alerts[0]["body"]


def test_wt_regime_no_alert_t_minus_4_or_2(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    today = _vn_today()
    _add_regime(db, emp, date_to=today + timedelta(days=4))
    _add_regime(
        db,
        db.query(Employee).filter(Employee.employee_code == "5290").one(),
        date_to=today + timedelta(days=2),
    )

    res = client.get("/api/ai/alerts/mine", headers=headers)
    assert res.status_code == 200
    assert _wt_alerts(res.json()) == []


def test_wt_regime_alert_idempotent(client, db):
    headers = _hr_headers(client)
    emp = db.query(Employee).filter(Employee.employee_code == "1514").one()
    target = _vn_today() + timedelta(days=3)
    regime = _add_regime(db, emp, date_to=target, regime_type="PREGNANT")

    first = client.get("/api/ai/alerts/mine", headers=headers).json()
    second = client.get("/api/ai/alerts/mine", headers=headers).json()
    wt1 = _wt_alerts(first)
    wt2 = _wt_alerts(second)
    assert len(wt1) == 1
    assert len(wt2) == 1
    assert wt1[0]["source_ref"] == f"wt_regime:{regime.id}:{target.isoformat()}"
