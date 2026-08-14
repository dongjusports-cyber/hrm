"""Chọn ODBC Driver SQL Server có trên máy — tránh lỗi IM002 trên .122."""

from __future__ import annotations

import re

_DRIVER_RE = re.compile(r"Driver=\{([^}]+)\}", re.IGNORECASE)

_PREFERRED = (
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
)


def installed_drivers() -> list[str]:
    try:
        import pyodbc  # type: ignore
    except ImportError:
        return []
    return list(pyodbc.drivers())


def pick_sql_server_driver() -> str | None:
    drivers = installed_drivers()
    if not drivers:
        return None
    installed = set(drivers)
    for name in _PREFERRED:
        if name in installed:
            return name
    for name in drivers:
        if "SQL Server" in name:
            return name
    return None


def configured_driver(conn_str: str) -> str | None:
    m = _DRIVER_RE.search(conn_str or "")
    return m.group(1) if m else None


def resolve_odbc_conn_str(conn_str: str) -> tuple[str, str | None]:
    """Trả về (conn_str đã sửa, tên driver thay thế hoặc None nếu giữ nguyên)."""
    conn_str = (conn_str or "").strip()
    if not conn_str:
        return conn_str, None
    current = configured_driver(conn_str)
    installed = set(installed_drivers())
    if current and current in installed:
        return conn_str, None
    picked = pick_sql_server_driver()
    if not picked:
        return conn_str, None
    if current:
        new_str = _DRIVER_RE.sub(f"Driver={{{picked}}}", conn_str, count=1)
    else:
        new_str = f"Driver={{{picked}}};{conn_str.lstrip(';')}"
    return new_str, picked


def odbc_setup_hint(conn_str: str) -> str:
    current = configured_driver(conn_str)
    installed = installed_drivers()
    if not installed:
        return (
            "Chưa có ODBC Driver SQL Server. Cài Driver 17 hoặc 18: "
            "https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server"
        )
    resolved, picked = resolve_odbc_conn_str(conn_str)
    if picked:
        return f"Driver '{current or '?'}' không có — dùng '{picked}'."
    if current and current not in installed:
        return f"Driver '{current}' không có trên máy. Có: {', '.join(installed)}"
    return f"Driver OK: {current}. ODBC: {', '.join(installed)}"
