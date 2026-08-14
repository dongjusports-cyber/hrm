"""Sửa MITAPRO_ODBC trong .env theo driver ODBC có trên máy."""

from __future__ import annotations

import sys
from pathlib import Path

from dj_agent.odbc_util import odbc_setup_hint, pick_sql_server_driver, resolve_odbc_conn_str


def _replace_mitapro_odbc_line(text: str, resolved: str) -> str:
    """Thay dòng MITAPRO_ODBC — không dùng re.sub (chuỗi ODBC có \\S gây lỗi)."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.lstrip()
        if not replaced and stripped.startswith("MITAPRO_ODBC="):
            out.append(f"MITAPRO_ODBC={resolved}\n")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and not out[-1].endswith("\n"):
            out[-1] = out[-1] + "\n"
        out.append(f"MITAPRO_ODBC={resolved}\n")
    return "".join(out)


def main() -> int:
    env_path = Path(".env")
    if not env_path.is_file():
        print("Không thấy .env — copy từ .env.hr122.example trước.")
        return 1

    text = env_path.read_text(encoding="utf-8")
    current = None
    for line in text.splitlines():
        if line.strip().startswith("MITAPRO_ODBC="):
            current = line.split("=", 1)[1].strip()
            break

    if current is None:
        picked = pick_sql_server_driver()
        if not picked:
            print(odbc_setup_hint(""))
            return 1
        default = (
            f"Driver={{{picked}}};"
            "Server=.\\SQLEXPRESS;Database=MITACOSQL;Trusted_Connection=yes;TrustServerCertificate=yes;"
        )
        text = text.rstrip() + f"\nMITAPRO_ODBC={default}\n"
        env_path.write_text(text, encoding="utf-8")
        print(f"Đã thêm MITAPRO_ODBC={default}")
        return 0

    resolved, picked = resolve_odbc_conn_str(current)
    if picked:
        env_path.write_text(_replace_mitapro_odbc_line(text, resolved), encoding="utf-8")
        print(f"Đã sửa driver → {picked}")
        print(resolved)
        return 0

    print(odbc_setup_hint(current))
    return 0


if __name__ == "__main__":
    sys.exit(main())
