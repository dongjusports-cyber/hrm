"""Khóa 1 MSNV trên 1 điện thoại — chống đưa TK cho bạn chấm hộ."""

from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.worker.service import MSG_ACCOUNT_OTHER_PHONE, msg_phone_bound_other
from tests.worker_auth import default_login_password, worker_login_json


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_first_login_binds_device(client, db):
    code = "5290"
    phone = "phone-alpha-5290xx"
    res = client.post(
        "/api/worker/login",
        json=worker_login_json(code, default_login_password(code), phone),
    )
    assert res.status_code == 200, res.text
    user = db.query(User).filter(User.username == code, User.role == "worker").one()
    assert user.worker_device_id == phone


def test_same_phone_cannot_login_other_msnv(client):
    phone = "phone-shared-factory"
    a = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), phone),
    )
    assert a.status_code == 200, a.text
    b = client.post(
        "/api/worker/login",
        json=worker_login_json("1514", default_login_password("1514"), phone),
    )
    assert b.status_code == 403
    assert b.json()["detail"] == msg_phone_bound_other("5290")


def test_same_msnv_cannot_login_other_phone(client):
    first = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), "phone-one-5290xxxx"),
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), "phone-two-5290xxxx"),
    )
    assert second.status_code == 403
    assert second.json()["detail"] == MSG_ACCOUNT_OTHER_PHONE


def test_same_msnv_same_phone_can_login_again(client):
    phone = "phone-stable-5290xxx"
    pw = default_login_password("5290")
    first = client.post("/api/worker/login", json=worker_login_json("5290", pw, phone))
    assert first.status_code == 200
    again = client.post("/api/worker/login", json=worker_login_json("5290", pw, phone))
    assert again.status_code == 200, again.text


def test_hr_unlock_clears_device_bind(client, db):
    code = "5290"
    old_phone = "phone-old-5290xxxxx"
    new_phone = "phone-new-5290xxxxx"
    first = client.post(
        "/api/worker/login",
        json=worker_login_json(code, default_login_password(code), old_phone),
    )
    assert first.status_code == 200

    emp = db.query(Employee).filter(Employee.employee_code == code).one()
    unlock = client.post(
        f"/api/employees/{emp.id}/unlock-reset-password",
        headers=_hr_headers(client),
    )
    assert unlock.status_code == 200, unlock.text
    assert "gỡ khóa điện thoại" in unlock.json()["detail"]

    db.expire_all()
    user = db.query(User).filter(User.username == code, User.role == "worker").one()
    assert user.worker_device_id is None

    ok = client.post(
        "/api/worker/login",
        json=worker_login_json(code, default_login_password(code), new_phone),
    )
    assert ok.status_code == 200, ok.text
    db.expire_all()
    user = db.query(User).filter(User.username == code, User.role == "worker").one()
    assert user.worker_device_id == new_phone


def test_old_phone_jwt_rejected_after_new_phone_bind(client, db):
    """JWT máy cũ không chấm hộ / không giữ phiên sau khi đã gắn máy mới."""
    code = "5290"
    pw = default_login_password(code)
    old_phone = "phone-old-jwt-5290x"
    new_phone = "phone-new-jwt-5290x"
    old = client.post("/api/worker/login", json=worker_login_json(code, pw, old_phone))
    assert old.status_code == 200
    old_token = old.json()["access_token"]

    emp = db.query(Employee).filter(Employee.employee_code == code).one()
    unlock = client.post(
        f"/api/employees/{emp.id}/unlock-reset-password",
        headers=_hr_headers(client),
    )
    assert unlock.status_code == 200
    fresh = client.post("/api/worker/login", json=worker_login_json(code, pw, new_phone))
    assert fresh.status_code == 200, fresh.text

    rejected = client.get(
        "/api/worker/me",
        headers={"Authorization": f"Bearer {old_token}", "X-Worker-Device-Id": old_phone},
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == MSG_ACCOUNT_OTHER_PHONE

    ok = client.get(
        "/api/worker/me",
        headers={
            "Authorization": f"Bearer {fresh.json()['access_token']}",
            "X-Worker-Device-Id": new_phone,
        },
    )
    assert ok.status_code == 200


def test_jwt_without_device_header_rejected_after_bind(client):
    """JWT đánh cắp, gọi API không kèm mã máy → không vào được."""
    token = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290")),
    ).json()["access_token"]
    res = client.get("/api/worker/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert res.json()["detail"] == MSG_ACCOUNT_OTHER_PHONE


