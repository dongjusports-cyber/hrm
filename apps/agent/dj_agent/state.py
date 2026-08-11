"""Watermark đồng bộ — lưu local trên máy Agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_last_sync_at(path: Path) -> datetime | None:
    raw = load_state(path).get("last_sync_at")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def set_last_sync_at(path: Path, when: datetime, *, extra: dict[str, Any] | None = None) -> None:
    data = load_state(path)
    data["last_sync_at"] = when.astimezone(timezone.utc).isoformat()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if extra:
        data.update(extra)
    save_state(path, data)
