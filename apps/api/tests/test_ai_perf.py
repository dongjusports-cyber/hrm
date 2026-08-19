"""Hàng rào hiệu năng AI — FAB poll không được compute_kpi / ghi DB.

Bài học HR-H002: GET poll 60s nếu ghi hoặc quét KPI cả nhà máy thì TTFB nổ trên 359 NV.
Badge dùng GET /api/ai/inbox?light=true — chỉ SELECT, không evaluate KPI.
400 NV: rà soát chấm lẻ phải COUNT tổng thật, không lấy len(limit=20).
"""

from __future__ import annotations

from datetime import datetime

from app.modules.ai.service import reset_kpi_eval_throttle_for_tests
from app.modules.attendance.engine import VN_TZ
from app.modules.attendance.models import AttendanceDay
from app.modules.mdm.models import Employee
from tests.test_employees_list_benchmark import EMP_COUNT, _SqlCounter, _seed_employees

MAX_INBOX_LIGHT_WRITES = 0
MAX_INBOX_LIGHT_HTTP = 35
MAX_ALERTS_SECOND_WRITES = 0
SCALE_EMP = 400
ODD_PUNCH_N = 87
MAX_PUNCH_REVIEW_SQL = 55
MAX_INBOX_LIGHT_SCALE_SQL = 40


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


def _seed_odd_punch_days(db, count: int) -> int:
    today = datetime.now(tz=VN_TZ).date()
    emps = (
        db.query(Employee)
        .filter(Employee.deleted_at.is_(None), Employee.status.in_(("active", "probation")))
        .limit(count)
        .all()
    )
    db.add_all(
        [
            AttendanceDay(
                employee_id=e.id,
                work_date=today,
                first_in=datetime(today.year, today.month, today.day, 8, 0, tzinfo=VN_TZ),
                last_out=None,
                punch_count=1,
                is_workday=True,
                source="machine",
            )
            for e in emps
        ]
    )
    db.commit()
    return len(emps)


def test_inbox_light_400nv_odd_punches_read_only(client, db):
    _seed_employees(db, SCALE_EMP)
    n = _seed_odd_punch_days(db, ODD_PUNCH_N)
    assert n == ODD_PUNCH_N
    headers = _hr_headers(client)
    client.get("/api/ai/inbox", headers=headers, params={"light": True})

    with _SqlCounter(db.get_bind()) as counter:
        res = client.get("/api/ai/inbox", headers=headers, params={"light": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["light"] is True
    assert body["todo_total"] >= 1
    todos = client.get("/api/ai/todos", headers=headers)
    assert todos.status_code == 200
    punch = next(c for c in todos.json()["cards"] if c["key"] == "punch_odd_current")
    assert punch["count"] == n
    print(f"\n[GET inbox light 400 NV + {ODD_PUNCH_N} chấm lẻ] SQL {counter.summary()}")
    assert len(counter.writes) <= MAX_INBOX_LIGHT_WRITES, counter.summary()
    assert len(counter.statements) <= MAX_INBOX_LIGHT_SCALE_SQL, counter.summary()


def test_punch_review_400nv_reports_true_total(client, db):
    _seed_employees(db, SCALE_EMP)
    n = _seed_odd_punch_days(db, ODD_PUNCH_N)
    headers = _admin_headers(client)
    with _SqlCounter(db.get_bind()) as counter:
        res = client.post(
            "/api/ai/query",
            headers=headers,
            json={"message": "Ai chấm lẻ tháng này"},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kind"] == "punch_review"
    assert body["model_name"] == "direct"
    assert f"Tổng {n} dòng" in body["answer"]
    assert "hiện 20" in body["answer"]
    print(f"\n[POST punch_review 400 NV] SQL {counter.summary()}")
    assert len(counter.statements) <= MAX_PUNCH_REVIEW_SQL, counter.summary()
