"""Cấu hình runtime từ biến môi trường — không hard-code secret."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_JWT = {
    "",
    "change_me_to_a_long_random_string",
}
WEAK_AGENT = {"", "change_me_agent_token"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DJ HRM"
    # local | production
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://djhrm:djhrm_local_change_me@localhost:5432/djhrm"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change_me_to_a_long_random_string"
    jwt_access_hours: int = 8
    jwt_refresh_days: int = 7
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    gemini_api_key: str = ""
    agent_token: str = "change_me_agent_token"
    # Hosts cho TrustedHostMiddleware khi production (vd: api.dongju.vn,localhost)
    trusted_hosts: str = "*"
    log_dir: str = "logs"
    # Ảnh hồ sơ NV (jpg/png/webp) — thư mục tương đối cwd API
    upload_dir: str = "data/uploads"
    # Bật OpenAPI /docs — tắt mặc định khi production
    docs_enabled: bool | None = None

    # Seed Admin (P0.5) — đổi mật khẩu ngay sau lần đăng nhập đầu
    admin_username: str = "admin"
    admin_password: str = "Admin@DongJu2026"
    admin_full_name: str = "Nguyễn Thanh Thiện"
    # True: tính công ngay trong request (test/dev). False: nền sau response (production Agent).
    sync_recalc_inline: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in ("production", "prod", "cloud")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        raw = [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]
        return raw or ["*"]

    @property
    def openapi_enabled(self) -> bool:
        if self.docs_enabled is not None:
            return self.docs_enabled
        return not self.is_production

    def validate_for_boot(self) -> tuple[list[str], list[str]]:
        """Cảnh báo / lỗi khi khởi động. Production: secret yếu → lỗi."""
        errors: list[str] = []
        warnings: list[str] = []
        if self.jwt_secret in WEAK_JWT or len(self.jwt_secret) < 24:
            msg = "JWT_SECRET còn mặc định/yếu — đổi trước khi lên Cloud."
            if self.is_production:
                errors.append(msg)
            else:
                warnings.append(msg)
        if self.agent_token in WEAK_AGENT:
            msg = "AGENT_TOKEN còn mặc định — Agent Mitapro sẽ không an toàn."
            if self.is_production:
                errors.append(msg)
            else:
                warnings.append(msg)
        if self.is_production and "*" in self.cors_origin_list:
            errors.append("CORS_ORIGINS không được dùng * trên production.")
        return errors, warnings


@lru_cache
def get_settings() -> Settings:
    return Settings()
