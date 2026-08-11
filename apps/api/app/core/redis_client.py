"""Redis — health check & cache/queue (Phase sau)."""

import redis

from app.core.config import get_settings

_settings = get_settings()
_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            _settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


def check_redis() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
