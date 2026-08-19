"""Tình huống thao tác nhà máy — khóa 1 MSNV / 1 điện thoại."""

from app.modules.core.models import User
from app.modules.mdm.models import Employee
from app.modules.worker.service import MSG_ACCOUNT_OTHER_PHONE, MSG_DEVICE_INVALID, msg_phone_bound_other
from tests.worker_auth import (
    default_login_password,
    unlocked_worker_headers,
    worker_auth_headers,
    worker_login_json,
)


def _hr_headers(client):
    token = client.post(
        "/api/auth/login", json={"username": "hr.demo", "password": "HrDemo@123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ban_cham_ho_dung_mat_khau_tren_may_ban(client):
    """A ở nhà đưa MSNV+pass cho B. B gõ trên điện thoại của B (đã khóa B)."""
    phone_a = "phone-scenario-a-xxxx"
    phone_b = "phone-scenario-b-xxxx"
    a = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), phone_a),
    )
    assert a.status_code == 200
    b = client.post(
        "/api/worker/login",
        json=worker_login_json("1514", default_login_password("1514"), phone_b),
    )
    assert b.status_code == 200
    ho = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), phone_b),
    )
    assert ho.status_code == 403
    assert ho.json()["detail"] == msg_phone_bound_other("1514")


def test_ban_cham_ho_may_moi_chua_khoa(client):
    """B xóa dữ liệu web / máy lạ, gõ MSNV A — A đã khóa máy nhà."""
    phone_a = "phone-a-home-5290xxx"
    assert (
        client.post(
            "/api/worker/login",
            json=worker_login_json("5290", default_login_password("5290"), phone_a),
        ).status_code
        == 200
    )
    stolen = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), "phone-b-cleared-xxxx"),
    )
    assert stolen.status_code == 403
    assert stolen.json()["detail"] == MSG_ACCOUNT_OTHER_PHONE


def test_ban_dung_msnv_minh_tren_may_da_khoa_nguoi_khac(client):
    """B cầm điện thoại A, gõ đúng mật khẩu B — vẫn chặn."""
    phone_a = "phone-a-only-5290xxx"
    assert (
        client.post(
            "/api/worker/login",
            json=worker_login_json("5290", default_login_password("5290"), phone_a),
        ).status_code
        == 200
    )
    b = client.post(
        "/api/worker/login",
        json=worker_login_json("1514", default_login_password("1514"), phone_a),
    )
    assert b.status_code == 403
    assert b.json()["detail"] == msg_phone_bound_other("5290")


def test_dang_xuat_roi_login_lai_cung_may(client):
    """Đăng xuất / mở lại app — cùng máy, cùng MSNV vẫn vào."""
    phone = "phone-reopen-5290xxxx"
    pw = default_login_password("5290")
    first = client.post("/api/worker/login", json=worker_login_json("5290", pw, phone))
    assert first.status_code == 200
    again = client.post("/api/worker/login", json=worker_login_json("5290", pw, phone))
    assert again.status_code == 200
    me = client.get("/api/worker/me", headers=worker_auth_headers(again.json()["access_token"], "5290", phone))
    assert me.status_code == 200
    assert me.json()["employee_code"] == "5290"


def test_sai_mat_khau_khong_gan_may(client, db):
    """Gõ sai pass không khóa máy cho tài khoản đó."""
    phone = "phone-badpass-5290xxx"
    bad = client.post("/api/worker/login", json=worker_login_json("5290", "sai", phone))
    assert bad.status_code == 401
    user = db.query(User).filter(User.username == "5290", User.role == "worker").one()
    assert user.worker_device_id is None
    ok = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), phone),
    )
    assert ok.status_code == 200
    db.expire_all()
    user = db.query(User).filter(User.username == "5290", User.role == "worker").one()
    assert user.worker_device_id == phone


def test_jwt_may_ban_khong_goi_duoc_api_cua_a(client):
    """Copy JWT A sang điện thoại B (mã máy B) — /me và không xem được hồ sơ A."""
    phone_a = "phone-jwt-a-5290xxxx"
    phone_b = "phone-jwt-b-1514xxxx"
    a = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), phone_a),
    )
    assert a.status_code == 200
    client.post(
        "/api/worker/login",
        json=worker_login_json("1514", default_login_password("1514"), phone_b),
    )
    stolen = client.get(
        "/api/worker/me",
        headers=worker_auth_headers(a.json()["access_token"], "5290", phone_b),
    )
    assert stolen.status_code == 403
    assert stolen.json()["detail"] == MSG_ACCOUNT_OTHER_PHONE


def test_thieu_device_id_khi_login(client):
    res = client.post(
        "/api/worker/login",
        json={"employee_code": "5290", "password": default_login_password("5290")},
    )
    assert res.status_code == 422


def test_device_id_khong_hop_le(client):
    res = client.post(
        "/api/worker/login",
        json=worker_login_json("5290", default_login_password("5290"), "bad id!!"),
    )
    assert res.status_code == 400
    assert res.json()["detail"] == MSG_DEVICE_INVALID


def test_ba_nguoi_cung_mot_may(client):
    """Máy truyền tay: người đầu gắn; hai người sau bị chặn."""
    phone = "phone-shared-line-xxxx"
    assert (
        client.post(
            "/api/worker/login",
            json=worker_login_json("5290", default_login_password("5290"), phone),
        ).status_code
        == 200
    )
    for code in ("1514", "1732"):
        res = client.post(
            "/api/worker/login",
            json=worker_login_json(code, default_login_password(code), phone),
        )
        assert res.status_code == 403
        assert res.json()["detail"] == msg_phone_bound_other("5290")


def test_hr_mo_khoa_roi_may_cu_khong_cham_cong_bang_jwt_cu(client, db):
    """HR mở khóa (đổi máy / mất máy): JWT cũ không chấm công được vì bắt đổi mật khẩu."""
    from app.modules.mdm.models import Team
    from app.modules.mdm.service import get_or_create_department_by_code

    code = "1732"
    headers = unlocked_worker_headers(client, code)
    dept = get_or_create_department_by_code(db, "03", "Main Office")
    team = Team(department_id=dept.id, code="T-03-SCEN", name="Main Office")
    db.add(team)
    db.flush()
    emp = db.query(Employee).filter(Employee.employee_code == code).one()
    emp.team_id = team.id
    db.commit()
    client.put(
        "/api/config/mobile-punch",
        headers={
            "Authorization": f"Bearer {client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@DongJu2026'}).json()['access_token']}"
        },
        json={"mode": "allowlist", "department_codes": ["03"], "require_photo": False},
    )

    unlock = client.post(
        f"/api/employees/{emp.id}/unlock-reset-password",
        headers=_hr_headers(client),
    )
    assert unlock.status_code == 200
    punch = client.post("/api/worker/punches", headers=headers, json={})
    assert punch.status_code == 403
    assert "đổi mật khẩu" in punch.json()["detail"]


def test_hr_mo_khoa_may_moi_gan_truoc_may_cu_khong_cuop_lai(client, db):
    """Đổi máy: login máy mới trước; máy cũ gõ lại pass không cướp khóa."""
    code = "5290"
    pw = default_login_password(code)
    old_phone = "phone-old-handset-xx"
    new_phone = "phone-new-handset-xx"
    assert client.post("/api/worker/login", json=worker_login_json(code, pw, old_phone)).status_code == 200
    emp = db.query(Employee).filter(Employee.employee_code == code).one()
    assert client.post(
        f"/api/employees/{emp.id}/unlock-reset-password",
        headers=_hr_headers(client),
    ).status_code == 200
    assert client.post("/api/worker/login", json=worker_login_json(code, pw, new_phone)).status_code == 200
    steal = client.post("/api/worker/login", json=worker_login_json(code, pw, old_phone))
    assert steal.status_code == 403
    assert steal.json()["detail"] == MSG_ACCOUNT_OTHER_PHONE
