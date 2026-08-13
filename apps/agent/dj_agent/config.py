"""Cấu hình Agent từ biến môi trường / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_AGENT_TOKENS = {"", "change_me_agent_token", "doi_trung_voi_AGENT_TOKEN_tren_VPS"}


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dj_api_base_url: str = "http://127.0.0.1:8000"
    dj_agent_token: str = "change_me_agent_token"
    # P6.1: bắt buộc HTTPS khi Agent trỏ Cloud VPS
    dj_agent_require_https: bool = False
    mitapro_odbc: str = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=.\\SQLEXPRESS;Database=MITACOSQL;Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    sync_interval_minutes: int = 2
    sync_overlap_minutes: int = 30
    sync_lookback_days: int = 3
    dj_agent_mock_sql: bool = False
    state_file: str = "./agent_state.json"
    agent_name: str = "dj-agent-mitapro"

    @property
    def state_path(self) -> Path:
        return Path(self.state_file)

    def validate_endpoint(self) -> list[str]:
        """Lỗi cấu hình trước khi sync (tiếng Việt)."""
        errors: list[str] = []
        base = (self.dj_api_base_url or "").strip().rstrip("/")
        if not base:
            errors.append("Thiếu DJ_API_BASE_URL.")
        elif self.dj_agent_require_https and not base.lower().startswith("https://"):
            errors.append(
                "DJ_API_BASE_URL phải dùng HTTPS khi kết nối Cloud "
                "(bật DJ_AGENT_REQUIRE_HTTPS=1)."
            )
        if self.dj_agent_require_https and self.dj_agent_token in WEAK_AGENT_TOKENS:
            errors.append("DJ_AGENT_TOKEN còn mặc định — đặt trùng AGENT_TOKEN trên VPS.")
        return errors


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
