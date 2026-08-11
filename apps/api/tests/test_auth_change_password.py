"""Staff đổi mật khẩu — xóa must_change_password."""


def test_change_password_clears_flag(client):
    created = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@DongJu2026"},
    )
    assert created.status_code == 200
    token = created.json()["access_token"]
    assert created.json()["user"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={
            "current_password": "Admin@DongJu2026",
            "new_password": "Admin@DongJu2026!",
        },
    )
    assert res.status_code == 200, res.text
    assert "đổi mật khẩu thành công" in res.json()["detail"]

    again = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@DongJu2026!"},
    )
    assert again.status_code == 200
    assert again.json()["user"]["must_change_password"] is False
