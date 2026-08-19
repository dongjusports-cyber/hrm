"""Worker self-service — login tự tạo TK, công tháng, phép năm."""

from datetime import date

from app.modules.worker.service import DEFAULT_WORKER_PASSWORD


def _worker_token(client, code: str) -> str:
    res = client.post(
        "/api/worker/login",
        json={"employee_code": code, "password": DEFAULT_WORKER_PASSWORD},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_worker_login_auto_provision(client, db):
    from app.modules.core.models import User
    from app.modules.mdm.models import Employee

    emp = db.query(Employee).filter(Employee.employee_code == "5290").first()
    assert emp is not None
    db.query(User).filter(User.username == "5290", User.role == "worker").delete()
    db.commit()

    token = _worker_token(client, "5290")
    user = db.query(User).filter(User.username == "5290", User.role == "worker").first()
    assert user is not None
    assert user.employee_id == emp.id

    me = client.get("/api/worker/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["employee_code"] == "5290"


def test_worker_leave_balance(client):
    token = _worker_token(client, "5290")
    res = client.get("/api/worker/leave-balance", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["year"] == date.today().year
    assert "accrued" in body and "used" in body and "remaining" in body
    assert body["days_per_year"] >= 12


def test_worker_attendance_month(client):
    token = _worker_token(client, "5290")
    res = client.get(
        "/api/worker/attendance",
        params={"period": "2026-08"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period"] == "2026-08"
    assert "days" in body
    assert isinstance(body["days"], list)
    if body["days"]:
        assert "punches" in body["days"][0]
