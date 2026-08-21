"""Worker self-service — đăng nhập, công tháng của chính mình, phép năm (service)."""

from datetime import date

from app.modules.core.models import User
from app.modules.worker.self_service import get_leave_balance
from tests.worker_auth import (
    default_login_password,
    unlocked_worker_headers,
    worker_auth_headers,
    worker_login_json,
)


def _login(client, code: str = "5290") -> tuple[str, dict]:
    res = client.post(
        "/api/worker/login",
        json=worker_login_json(code, default_login_password(code)),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    return body["access_token"], body["worker"]


def test_worker_login_seeded_account(client):
    token, worker = _login(client, "5290")
    assert worker["employee_code"] == "5290"
    assert worker["must_change_password"] is True

    me = client.get("/api/worker/me", headers=worker_auth_headers(token))
    assert me.status_code == 200, me.text
    assert me.json()["employee_code"] == "5290"


def test_worker_leave_balance_service(client, db):
    user = db.query(User).filter(User.username == "5290", User.role == "worker").first()
    assert user is not None

    out = get_leave_balance(db, user, as_of=date(date.today().year, 8, 1))
    assert out.year == date.today().year
    assert out.days_per_year >= 12
    assert out.accrued >= 0 and out.used >= 0 and out.remaining >= 0


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
