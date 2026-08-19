"""Hàng rào hiệu năng AI — FAB poll không được compute_kpi / ghi DB.

Bài học HR-H002: GET poll 60s nếu ghi hoặc quét KPI cả nhà máy thì TTFB nổ trên 359 NV.
Badge dùng GET /api/ai/inbox?light=true — chỉ SELECT, không evaluate KPI.
"""

from __future__ import annotations

from app.modules.ai.service import reset_kpi_eval_throttle_for_tests
from tests.test_employees_list_benchmark import EMP_COUNT, _SqlCounter, _seed_employees

MAX_INBOX_LIGHT_WRITES = 0
MAX_INBOX_LIGHT_HTTP = 35
MAX_ALERTS_SECOND_WRITES = 0


def _hr_headers(client) -> dict[str, str]:
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(client) -> dict[str, str]:
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin@DongJu2026"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_inbox_light_read_only_and_bounded_sql(client, db):
    _seed_employees(db, EMP_COUNT)
    headers = _hr_headers(client)
    client.get("/api/ai/inbox", headers=headers, params={"light": True})

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get("/api/ai/inbox", headers=headers, params={"light": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["light"] is True
    assert "todo_total" in body
    assert body["alerts"] == []
    assert body["cards"] == []
    print(f"\n[GET /api/ai/inbox?light=true] SQL {counter.summary()}")
    assert len(counter.writes) <= MAX_INBOX_LIGHT_WRITES, counter.summary()
    assert len(counter.statements) <= MAX_INBOX_LIGHT_HTTP, counter.summary()


def test_alerts_mine_second_request_no_writes(client, db):
    """Lần 2 không INSERT (source_ref) và không chạy lại KPI vừa quét."""
    reset_kpi_eval_throttle_for_tests()
    headers = _hr_headers(client)
    first = client.get("/api/ai/alerts/mine", headers=headers)
    assert first.status_code == 200

    with _SqlCounter(db.get_bind()) as counter:
        second = client.get("/api/ai/alerts/mine", headers=headers)
    assert second.status_code == 200
    print(f"\n[GET /api/ai/alerts/mine lần 2] SQL {counter.summary()}")
    assert len(counter.writes) <= MAX_ALERTS_SECOND_WRITES, counter.summary()


def test_inbox_full_has_briefing_suggestion(client, db):
    headers = _hr_headers(client)
    res = client.get("/api/ai/inbox", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["light"] is False
    labels = [s["label"] for s in body["suggestions"]]
    assert "Tóm tắt hôm nay" in labels


def test_ai_query_daily_briefing_direct(client, db):
    res = client.post(
        "/api/ai/query",
        headers=_admin_headers(client),
        json={"message": "Tóm tắt việc cần làm hôm nay"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "daily_briefing"
    assert body["model_name"] == "direct"
    assert "Tóm tắt việc cần làm hôm nay" in body["answer"]
    assert body.get("suggestions")
