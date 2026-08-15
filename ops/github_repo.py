"""Cau hinh repo GitHub — doc tu ops/github.repo."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_CFG = ROOT / "ops" / "github.repo"


def _load() -> dict[str, str]:
    data: dict[str, str] = {}
    for line in _CFG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, val = line.partition("=")
        data[key.strip()] = val.strip()
    return data


_cfg = _load()
OWNER = _cfg["OWNER"]
REPO = _cfg["REPO"]
HTTPS = _cfg["HTTPS"]
SSH = _cfg["SSH"]
DEPLOY_KEYS_URL = _cfg["DEPLOY_KEYS_URL"]
REPO_HOME = _cfg["REPO_HOME"]
