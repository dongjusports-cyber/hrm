#!/usr/bin/env python3
"""Do hieu nang GET /api/employees tren VPS — HTTP (TTFB) + so cau SQL.

Dung: python ops\\bench_employees_vps.py    (can ops/vps-root.txt)

Hai phep do bo sung nhau:
  - HTTP: TTFB vs transfer -> biet cham o server hay o mang/payload.
  - SQL:  so cau SQL tren Session moi -> biet co N+1 hay co ghi tren duong doc.
Chi doc, khong commit gi vao DB production.
"""
from __future__ import annotations

import io
from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
CRED = ROOT / "ops" / "vps-root.txt"


def main() -> None:
    if not CRED.is_file():
        raise SystemExit("Thieu ops/vps-root.txt (IP + pass root VPS)")
    lines = [
        line.strip()
        for line in CRED.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    ip, pw = lines[0], lines[1]

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ip, username="root", password=pw, timeout=60)

    def put(local: str, remote: str) -> None:
        data = (ROOT / local).read_bytes().replace(b"\r\n", b"\n")
        with SCPClient(c.get_transport()) as scp:
            scp.putfo(io.BytesIO(data), remote)

    def run(cmd: str, label: str) -> None:
        _, out, err = c.exec_command(cmd, timeout=600)
        text = out.read().decode("utf-8", errors="replace").strip()
        problem = err.read().decode("utf-8", errors="replace").strip()
        print(f"===== {label} =====")
        print(text or "(khong co ket qua)")
        if problem and "bcrypt" not in problem.lower():
            print("--- stderr ---")
            print(problem)
        print()

    put("ops/bench_employees_http_remote.py", "/root/bench_employees_http_remote.py")
    run("python3 /root/bench_employees_http_remote.py", "HTTP: TTFB vs transfer")

    put("ops/bench_employees_sql_remote.py", "/root/bench_employees_sql_remote.py")
    run(
        "docker cp /root/bench_employees_sql_remote.py "
        "djhrm-api:/app/bench_employees_sql_remote.py && "
        "docker compose -f /opt/dj-hrm/docker-compose.prod.yml "
        "--env-file /opt/dj-hrm/.env.prod exec -T api "
        "python /app/bench_employees_sql_remote.py",
        "SQL: so cau lenh tren Session moi",
    )
    c.close()


if __name__ == "__main__":
    main()
