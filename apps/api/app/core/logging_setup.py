"""Log file + rotate (12§12.8) — không ghi mật khẩu / API key / lương chi tiết."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings


def setup_logging(settings: Settings) -> None:
    root = logging.getLogger()
    if getattr(root, "_djhrm_configured", False):
        return

    level = logging.INFO if settings.is_production else logging.DEBUG
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(level)
        root.addHandler(sh)

    log_dir = Path(settings.log_dir)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "djhrm-api.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.INFO)
        root.addHandler(fh)
    except OSError:
        logging.getLogger(__name__).warning("Trợ Lý AI: không tạo được thư mục log %s", log_dir)

    root._djhrm_configured = True  # type: ignore[attr-defined]
