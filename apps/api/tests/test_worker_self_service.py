"""Worker self-service — công tháng, số dư phép năm (GET không ghi DB)."""

from datetime import date

from sqlalchemy import event

from tests.worker_auth import (
    default_login_password,
    unlocked_worker_headers,
    worker_auth_headers,
    worker_login_json,
)


def _worker_headers(client, code: str = "5290") -> dict[str, str]:
    res = client.post(
        "/api/worker/login",
        json=worker_login_json(code, default_login_password(code)),
    )
    assert res.status_code == 200, res.text
    return worker_auth_headers(res.json()["access_token"], code)


def test_worker_login_seeded_account(client, db):
    from app.modules.core.models import User
    from app.modules.mdm.models import Employee

    emp = db.query(Employee).filter(Employee.employee_code == "5290").first()
    assert emp is not None
    user = db.query(User).filter(User.username == "5290", User.role == "worker").first()
    assert user is not None

    headers = _worker_headers(client, "5290")
    me = client.get("/api/worker/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["employee_code"] == "5290"


def test_worker_unknown_msnv_does_not_auto_create(client, db):
    from app.modules.core.models import User

    res = client.post(
        "/api/worker/login",
        json=worker_login_json("9999", "9999"),
    )
    assert res.status_code == 401
    assert db.query(User).filter(User.username == "9999", User.role == "worker").first() is None


def test_worker_leave_balance(client):
    headers = _worker_headers(client, "5290")
    res = client.get("/api/worker/leave-balance", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["year"] == date.today().year
    assert "accrued" in body and "used" in body and "remaining" in body
    assert float(body["days_per_year"]) >= 12
    assert float(body["remaining"]) >= 0


def test_worker_leave_balance_get_is_readonly(client, db):
    headers = _worker_headers(client, "5290")
    warm = client.get("/api/worker/leave-balance", headers=headers)
    assert warm.status_code == 200, warm.text

    statements: list[str] = []

    def _record(conn, cursor, statement, params, context, executemany) -> None:
        statements.append(statement.strip().split(maxsplit=1)[0].upper())

    bind = db.get_bind()
    event.listen(bind, "before_cursor_execute", _record)
    try:
        res = client.get("/api/worker/leave-balance", headers=headers)
    finally:
        event.remove(bind, "before_cursor_execute", _record)

    assert res.status_code == 200, res.text
    writes = [s for s in statements if s in ("INSERT", "UPDATE", "DELETE")]
    assert writes == [], f"GET /worker/leave-balance ghi DB: {writes} / {statements}"


def test_worker_attendance_month(client):
    headers = unlocked_worker_headers(client, "5290")
    res = client.get(
        "/api/worker/attendance",
        params={"period": "2026-08"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period"] == "2026-08"
    assert "days" in body
    assert isinstance(body["days"], list)
    if body["days"]:
        assert "punches" in body["days"][0]
