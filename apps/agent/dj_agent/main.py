"""
DJ Sync Agent — entrypoint
Chạy trên máy Windows có Mitapro:

  cd apps/agent
  copy config.example.env .env
  pip install -r requirements.txt
  python -m dj_agent.main
  python -m dj_agent.main --once
  python -m dj_agent.main --mock --once
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dj_agent.config import get_settings
from dj_agent.odbc_util import odbc_setup_hint, resolve_odbc_conn_str
from dj_agent.pusher import ApiPusher
from dj_agent.sql_reader import PunchRow, build_source
from dj_agent.sync_loop import process_pending, run_forever, run_once


def _setup_logging() -> None:
    log_file = Path(__file__).resolve().parent.parent / "agent.log"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )


def _demo_mock_rows() -> list[PunchRow]:
    now = datetime.now(timezone(timedelta(hours=7)))
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return [
        PunchRow("5290", day.replace(hour=8, minute=2), "MOCK-FP-5290"),
        PunchRow("5290", day.replace(hour=17, minute=5), "MOCK-FP-5290"),
        PunchRow("1514", day.replace(hour=8, minute=0), "MOCK-FP-1514"),
        PunchRow("1514", day.replace(hour=17, minute=1), "MOCK-FP-1514"),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DJ Sync Agent — Mitapro → DJ HRM")
    parser.add_argument("--once", action="store_true", help="Chạy 1 vòng sync rồi thoát")
    parser.add_argument("--mock", action="store_true", help="Dùng dữ liệu giả (không cần SQL Server)")
    parser.add_argument("--pending-only", action="store_true", help="Chỉ xử lý job Đồng bộ ngay")
    args = parser.parse_args(argv)

    _setup_logging()
    settings = get_settings()
    if args.mock:
        settings.dj_agent_mock_sql = True

    cfg_errors = settings.validate_endpoint()
    if cfg_errors:
        for msg in cfg_errors:
            logging.getLogger("dj_agent").error("Trợ Lý AI: %s", msg)
        return 2

    odbc = settings.mitapro_odbc
    if not settings.dj_agent_mock_sql:
        odbc, picked = resolve_odbc_conn_str(odbc)
        if picked:
            logging.getLogger("dj_agent").warning(
                "ODBC: tự chuyển sang driver '%s' (sửa MITAPRO_ODBC trong .env cho cố định).",
                picked,
            )
        elif odbc:
            hint = odbc_setup_hint(settings.mitapro_odbc)
            if "Không có" in hint or "Chưa có" in hint:
                logging.getLogger("dj_agent").error("Trợ Lý AI: %s", hint)

    source = build_source(
        mock=settings.dj_agent_mock_sql,
        odbc=odbc,
        mock_rows=_demo_mock_rows() if settings.dj_agent_mock_sql else None,
    )
    pusher = ApiPusher(
        settings.dj_api_base_url,
        settings.dj_agent_token,
        agent_name=settings.agent_name,
        push_chunk_size=settings.push_chunk_size,
    )

    try:
        if args.pending_only:
            n = process_pending(settings, source, pusher)
            logging.getLogger("dj_agent").info("Đã xử lý %s pending job", n)
            return 0
        if args.once or settings.sync_interval_minutes <= 0:
            pending_done = process_pending(settings, source, pusher)
            if pending_done == 0:
                run_once(settings, source, pusher, reason="once")
            return 0
        run_forever(settings, source, pusher)
        return 0
    except KeyboardInterrupt:
        logging.getLogger("dj_agent").info("Agent dừng (Ctrl+C).")
        return 0
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("dj_agent").error("%s", exc)
        return 1
    finally:
        pusher.close()


if __name__ == "__main__":
    sys.exit(main())
