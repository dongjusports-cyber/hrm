#!/usr/bin/env python3
"""Kéo DB production VPS → Docker Postgres máy nhà.

Chỉ ĐỌC VPS (pg_dump). Không restore / seed / ghi dữ liệu lên VPS.
Ghi đè DB Docker local. File dump gitignore (backups/).
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
CRED = ROOT / "ops" / "vps-root.txt"
BACKUP_DIR = ROOT / "backups"
REMOTE_DUMP = "/root/djhrm_vps_latest.dump"
CONTAINER = "djhrm-postgres"
PGUSER = "djhrm"
PGDB = "djhrm"


def _ssh() -> paramiko.SSHClient:
    if not CRED.is_file():
        print("Thieu ops/vps-root.txt")
        raise SystemExit(1)
    lines = [
        ln.strip()
        for ln in CRED.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    ip, pw = lines[0], lines[1]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", password=pw, timeout=60)
    return client


def _run_ssh(client: paramiko.SSHClient, cmd: str, timeout: int = 300) -> str:
    _, out, err = client.exec_command(cmd, timeout=timeout)
    stdout = out.read().decode("utf-8", errors="replace")
    stderr = err.read().decode("utf-8", errors="replace")
    code = out.channel.recv_exit_status()
    if code != 0:
        print(stderr or stdout)
        raise SystemExit(f"VPS lenh loi ({code}): {cmd[:80]}")
    return stdout


def _docker(*args: str) -> None:
    r = subprocess.run(["docker", *args], cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"docker {' '.join(args)} that bai ({r.returncode})")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_dump = BACKUP_DIR / f"djhrm_vps_{stamp}.dump"
    latest = BACKUP_DIR / "djhrm_vps_latest.dump"

    print("== 1/4 Dump DB tren VPS (chi doc) ==")
    client = _ssh()
    _run_ssh(
        client,
        "docker exec djhrm-postgres pg_dump -U djhrm -d djhrm -Fc -f /tmp/djhrm_vps.dump"
        " && docker cp djhrm-postgres:/tmp/djhrm_vps.dump "
        + REMOTE_DUMP
        + " && docker exec djhrm-postgres rm -f /tmp/djhrm_vps.dump",
        timeout=420,
    )
    print("== 2/4 Tai dump ve may nha ==")
    with SCPClient(client.get_transport()) as scp:
        scp.get(REMOTE_DUMP, str(local_dump))
    client.close()
    if latest.exists():
        latest.unlink()
    latest.write_bytes(local_dump.read_bytes())
    kb = local_dump.stat().st_size // 1024
    print(f"    {local_dump.name}  ({kb} KB)")

    print("== 3/4 Restore vao Docker local (ghi de DB nha, khong dung VPS) ==")
    subprocess.run(["docker", "stop", "djhrm-api"], cwd=ROOT, check=False)
    _docker("cp", str(local_dump), f"{CONTAINER}:/tmp/djhrm_restore.dump")
    term = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "psql",
            "-U",
            PGUSER,
            "-d",
            "postgres",
            "-c",
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname='{PGDB}' AND pid <> pg_backend_pid();",
        ],
        cwd=ROOT,
        capture_output=True,
    )
    restore = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "pg_restore",
            "-U",
            PGUSER,
            "-d",
            PGDB,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            "/tmp/djhrm_restore.dump",
        ],
        cwd=ROOT,
    )
    subprocess.run(
        ["docker", "exec", CONTAINER, "rm", "-f", "/tmp/djhrm_restore.dump"],
        cwd=ROOT,
        check=False,
    )
    if restore.returncode not in (0, 1):
        raise SystemExit(f"pg_restore loi ({restore.returncode})")
    if term.returncode != 0:
        print("(canh bao: ngat ket noi cu — tiep tuc)")

    print("== 4/4 Khoi dong API local + dem NV ==")
    subprocess.run(["docker", "start", "djhrm-api"], cwd=ROOT, check=False)
    count = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "psql",
            "-U",
            PGUSER,
            "-d",
            PGDB,
            "-tAc",
            "SELECT count(*) FROM employees WHERE deleted_at IS NULL;",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    nv = (count.stdout or "").strip()
    print(f"    NV local (chua xoa): {nv}")
    print()
    print("XONG — DB nha = ban copy tu VPS. VPS khong bi ghi de.")
    print("Portal local: http://localhost:5173  (Ctrl+F5)")


if __name__ == "__main__":
    main()
