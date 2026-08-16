"""Đăng nhập worker đã đổi mật khẩu — dùng cho API phiếu lương (QA-03)."""

from fastapi.testclient import TestClient

from app.modules.worker.service import default_password_from_cccd

WORKER_UNLOCKED_PASSWORD = "Worker@DongJu1"


def default_login_password(code: str, id_number: str | None = None) -> str:
    """Mật khẩu mặc định của NV seed (không CCCD → 4 số cuối MSNV)."""
    return default_password_from_cccd(id_number, code)


def unlocked_worker_headers(client: TestClient, code: str = "5290") -> dict[str, str]:
    default_pw = default_login_password(code)
    login = client.post(
        "/api/worker/login",
        json={"employee_code": code, "password": default_pw},
    )
    if login.status_code != 200:
        login = client.post(
            "/api/worker/login",
            json={"employee_code": code, "password": WORKER_UNLOCKED_PASSWORD},
        )
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    body = login.json()
    token = body["access_token"]
    if body["worker"]["must_change_password"]:
        changed = client.post(
            "/api/worker/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": default_pw,
                "new_password": WORKER_UNLOCKED_PASSWORD,
            },
        )
        assert changed.status_code == 200, changed.text
        login = client.post(
            "/api/worker/login",
            json={"employee_code": code, "password": WORKER_UNLOCKED_PASSWORD},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
