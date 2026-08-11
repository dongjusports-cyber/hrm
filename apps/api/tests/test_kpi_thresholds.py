"""KPI ngưỡng policy + alert rule-based (02§2.4 / 04§4.6)."""

from app.modules.ai.service import evaluate_kpi_threshold_alerts
from app.modules.policy.models import PolicyPackage
from app.modules.policy.seed_payload import default_payload


def _admin_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_default_payload_has_kpi_keys():
    p = default_payload()
    assert "kpi_attendance_min_pct" in p
    assert "kpi_ot_dept_max_pct" in p


def test_policy_save_merges_kpi_keys(client, db):
    headers = _admin_headers(client)
    pkg = db.query(PolicyPackage).filter(PolicyPackage.is_active.is_(True)).first()
    assert pkg is not None
    # giả lập gói cũ thiếu khóa KPI
    old = {k: v for k, v in pkg.payload.items() if not str(k).startswith("kpi_")}
    pkg.payload = old
    db.commit()

    for step in (1, 2, 3):
        res = client.put(
            f"/api/policies/packages/{pkg.id}",
            headers={**headers, "X-Confirm-Step": str(step)},
            json={"name": pkg.name, "payload": {**old, "kpi_attendance_min_pct": 85}},
        )
        assert res.status_code == 200, res.text
    assert res.json()["status"] == "saved"
    db.refresh(pkg)
    assert pkg.payload["kpi_attendance_min_pct"] == 85
    assert "kpi_hours_per_day" in pkg.payload


def test_kpi_threshold_alerts(client, db):
    pkg = db.query(PolicyPackage).filter(PolicyPackage.is_active.is_(True)).first()
    assert pkg is not None
    payload = dict(pkg.payload)
    payload.update(default_payload())
    # Ngưỡng cực thấp/cao để chắc chắn bắn alert trên kỳ seed
    payload["kpi_attendance_min_pct"] = 99.9
    payload["kpi_ot_rate_max_pct"] = 0.001
    payload["kpi_turnover_max_pct"] = 0.001
    payload["kpi_ot_dept_max_pct"] = 0.001
    pkg.payload = payload
    db.commit()

    # ensure pay period + KPI compute
    headers = _admin_headers(client)
    assert client.get("/api/reports/kpi?period=2025-10", headers=headers).status_code == 200

    evaluate_kpi_threshold_alerts(db, period="2025-10")
    alerts = client.get("/api/ai/alerts/mine", headers=headers)
    assert alerts.status_code == 200
    keys = {a["rule_key"] for a in alerts.json()["alerts"]}
    assert "kpi_attendance_low" in keys or "kpi_ot_high" in keys or "kpi_turnover_high" in keys
