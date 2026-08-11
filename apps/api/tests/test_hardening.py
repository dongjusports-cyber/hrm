"""P5.4 — hardening cấu hình production."""

from app.core.config import Settings, WEAK_JWT


def test_production_rejects_weak_secrets():
    s = Settings(
        app_env="production",
        jwt_secret="change_me_to_a_long_random_string",
        agent_token="change_me_agent_token",
        cors_origins="https://djhrm.example.com",
    )
    errors, _ = s.validate_for_boot()
    assert any("JWT_SECRET" in e for e in errors)
    assert any("AGENT_TOKEN" in e for e in errors)


def test_production_rejects_cors_star():
    s = Settings(
        app_env="production",
        jwt_secret="a" * 32,
        agent_token="b" * 32,
        cors_origins="*",
    )
    errors, _ = s.validate_for_boot()
    assert any("CORS" in e for e in errors)


def test_local_weak_secret_is_warning_only():
    s = Settings(
        app_env="local",
        jwt_secret=next(iter(WEAK_JWT - {""})),
        agent_token="change_me_agent_token",
    )
    errors, warnings = s.validate_for_boot()
    assert errors == []
    assert warnings


def test_health_exposes_env(client):
    res = client.get("/health")
    assert res.status_code in (200, 503)
    body = res.json()
    assert body["version"].startswith("0.6.")
    assert "env" in body
