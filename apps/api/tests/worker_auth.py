"""Đăng nhập worker đã đổi mật khẩu — dùng cho API phiếu lương (QA-03)."""

from fastapi.testclient import TestClient

from app.modules.worker.service import default_password_from_cccd

WORKER_UNLOCKED_PASSWORD = "Worker@DongJu1"


def default_login_password(code: str, id_number: str | None = None) -> str:
    """Mật khẩu mặc định của NV seed (không CCCD → 4 số cuối MSNV)."""
    return default_password_from_cccd(id_number, code)


def worker_device_id_for(code: str, device_id: str | None = None) -> str:
    return device_id or f"pytest-phone-{code}"


def worker_login_json(code: str, password: str, device_id: str | None = None) -> dict[str, str]:
    """Body login worker — mỗi MSNV test một «máy» riêng trừ khi truyền device_id."""
    return {
        "employee_code": code,
        "password": password,
        "device_id": worker_device_id_for(code, device_id),
    }


def worker_auth_headers(token: str, code: str = "5290", device_id: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Worker-Device-Id": worker_device_id_for(code, device_id),
    }


def unlocked_worker_headers(client: TestClient, code: str = "5290") -> dict[str, str]:
    default_pw = default_login_password(code)
    device_id = worker_device_id_for(code)
    login = client.post("/api/worker/login", json=worker_login_json(code, default_pw, device_id))
    if login.status_code != 200:
        login = client.post(
            "/api/worker/login",
            json=worker_login_json(code, WORKER_UNLOCKED_PASSWORD, device_id),
        )
        assert login.status_code == 200, login.text
        return worker_auth_headers(login.json()["access_token"], code, device_id)

    body = login.json()
    token = body["access_token"]
    if body["worker"]["must_change_password"]:
        changed = client.post(
            "/api/worker/change-password",
            headers=worker_auth_headers(token, code, device_id),
            json={
                "current_password": default_pw,
                "new_password": WORKER_UNLOCKED_PASSWORD,
            },
        )
        assert changed.status_code == 200, changed.text
        login = client.post(
            "/api/worker/login",
            json=worker_login_json(code, WORKER_UNLOCKED_PASSWORD, device_id),
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
    return worker_auth_headers(token, code, device_id)
