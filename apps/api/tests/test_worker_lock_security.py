"""Bảo mật Worker — nghỉ việc + khóa 3 lần + HR unlock/reset."""

from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.worker.service import DEFAULT_WORKER_PASSWORD


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_worker_wrong_password_shows_remaining(client):
    res = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": "sai"},
    )
    assert res.status_code == 401
    assert "còn 2 lần thử" in res.json()["detail"]


def test_worker_lock_after_3_failures(client, db):
    code = "5290"
    for _ in range(2):
        bad = client.post("/api/worker/login", json={"employee_code": code, "password": "sai"})
        assert bad.status_code == 401
    locked = client.post("/api/worker/login", json={"employee_code": code, "password": "sai"})
    assert locked.status_code == 423
    assert "khóa do nhập sai mật khẩu 3 lần" in locked.json()["detail"]

    still = client.post(
        "/api/worker/login",
        json={"employee_code": code, "password": DEFAULT_WORKER_PASSWORD},
    )
    assert still.status_code == 423

    emp = db.query(Employee).filter(Employee.employee_code == code).first()

    unlock = client.post(
        f"/api/employees/{emp.id}/unlock-reset-password",
        headers=_hr_headers(client),
    )
    assert unlock.status_code == 200, unlock.text
    assert unlock.json()["new_password"] == DEFAULT_WORKER_PASSWORD

    ok = client.post(
        "/api/worker/login",
        json={"employee_code": code, "password": DEFAULT_WORKER_PASSWORD},
    )
    assert ok.status_code == 200, ok.text


def test_resigned_worker_cannot_login(client, db):
    emp = db.query(Employee).filter(Employee.employee_code == "1514").first()
    emp.status = "resigned"
    user = (
        db.query(User)
        .filter(User.username == "1514", User.role == "worker")
        .first()
    )
    user.is_active = False
    db.commit()

    res = client.post(
        "/api/worker/login",
        json={"employee_code": "1514", "password": DEFAULT_WORKER_PASSWORD},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "Tài khoản đã ngưng hoạt động do nhân sự đã nghỉ việc."


def test_employee_list_includes_account_status(client):
    res = client.get("/api/employees", headers=_hr_headers(client))
    assert res.status_code == 200
    rows = res.json()
    assert rows
    assert "account_status" in rows[0]
    assert "account_status_label" in rows[0]
