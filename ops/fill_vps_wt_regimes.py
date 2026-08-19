#!/usr/bin/env python3
"""Nạp danh sách chế độ thai sản / nuôi con nhỏ (Excel 18.08) lên VPS.

Chạy từ máy .123 (không cần deploy trước — copy script vào container):

  python ops/fill_vps_wt_regimes.py
"""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
XLSX_DIR = ROOT / "Dữ liệu nhân viên" / "Dữ liệu công nhân"
SCRIPT = ROOT / "apps" / "api" / "app" / "scripts" / "import_wt_regimes.py"


def _ssh() -> tuple[str, str]:
    lines = [
        ln.strip()
        for ln in (ROOT / "ops" / "vps-root.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    return lines[0], lines[1]


def _find_xlsx() -> Path:
    matches = [
        p
        for p in (
            list(XLSX_DIR.glob("*thai sản*.xlsx"))
            + list(XLSX_DIR.glob("*thai san*.xlsx"))
            + list(XLSX_DIR.glob("*nuôi con*.xlsx"))
            + list(XLSX_DIR.glob("*nuoi con*.xlsx"))
        )
        if not p.name.startswith("~$")
    ]
    # unique, newest name last (18.08)
    uniq = sorted({p.resolve() for p in matches}, key=lambda p: p.name)
    if not uniq:
        raise SystemExit(f"Không thấy file chế độ thai sản/nuôi con .xlsx trong {XLSX_DIR}")
    return uniq[-1]


def _exec(client: paramiko.SSHClient, cmd: str, timeout: int = 300) -> str:
    print("→", cmd)
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    if code != 0:
        raise SystemExit(f"Lệnh VPS lỗi ({code}): {cmd}")
    return out


def main() -> None:
    xlsx = _find_xlsx()
    if not SCRIPT.is_file():
        raise SystemExit(f"Không thấy {SCRIPT}")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(xlsx, arcname="che_do.xlsx")
        tar.add(SCRIPT, arcname="import_wt_regimes.py")
    payload = buf.getvalue()
    print(f"Gói {xlsx.name} ({len(payload) / 1e3:.0f} KB)")

    ip, pw = _ssh()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", password=pw, timeout=60)
    try:
        with SCPClient(client.get_transport()) as scp:
            scp.putfo(io.BytesIO(payload), "/tmp/che_do.tar.gz")
        _exec(
            client,
            "rm -rf /tmp/che_do && mkdir -p /tmp/che_do && tar -xzf /tmp/che_do.tar.gz -C /tmp/che_do",
        )
        _exec(client, "docker cp /tmp/che_do/che_do.xlsx djhrm-api:/tmp/che_do.xlsx")
        _exec(client, "docker cp /tmp/che_do/import_wt_regimes.py djhrm-api:/tmp/import_wt_regimes.py")
        _exec(
            client,
            "docker exec -w /app -e PYTHONPATH=/app djhrm-api python /tmp/import_wt_regimes.py --xlsx /tmp/che_do.xlsx",
            timeout=600,
        )
        _exec(client, "rm -rf /tmp/che_do /tmp/che_do.tar.gz")
    finally:
        client.close()
    print("XONG — F5 Portal → Nhân sự → lọc Chế độ đặc biệt, mở hồ sơ NV kiểm tra tab chế độ.")


if __name__ == "__main__":
    main()
