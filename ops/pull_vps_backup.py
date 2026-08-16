#!/usr/bin/env python3
"""Keo file backup Postgres moi nhat tu VPS ve may nay (phong VPS hong)."""
from __future__ import annotations

from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
CRED = ROOT / "ops" / "vps-root.txt"
DEST = ROOT / "backups"
REMOTE_DIR = "/opt/dj-hrm/backups"


def main() -> None:
    if not CRED.is_file():
        raise SystemExit(f"Thieu {CRED} — copy tu may nha (gitignore).")
    lines = [
        ln.strip()
        for ln in CRED.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    ip, pw = lines[0], lines[1]
    DEST.mkdir(parents=True, exist_ok=True)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ip, username="root", password=pw, timeout=60)
    _, o, e = c.exec_command(
        f"ls -1t {REMOTE_DIR}/djhrm_*.dump 2>/dev/null | head -1", timeout=30
    )
    remote = o.read().decode("utf-8", "replace").strip()
    err = e.read().decode("utf-8", "replace").strip()
    if not remote:
        c.close()
        raise SystemExit(f"Khong thay file dump tren VPS. {err}")

    local = DEST / Path(remote).name
    print(f"Keo {remote} -> {local}")
    with SCPClient(c.get_transport()) as scp:
        scp.get(remote, str(local))
    c.close()
    print(f"Xong: {local} ({local.stat().st_size} bytes)")
    print("Giu file nay o USB / may .123 — khong commit Git.")


if __name__ == "__main__":
    main()
