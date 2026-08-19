#!/usr/bin/env python3
"""Nạp Thông tin bổ sung 14.08 (hôn nhân, số con, SĐT, STK trống) lên VPS.

Không xóa NV. Chạy từ máy .123 SAU khi đã deploy code mới:

  python ops/fill_vps_thong_tin_bo_sung.py
"""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
XLSX_DIR = ROOT / "Dữ liệu nhân viên" / "Dữ liệu công nhân"
COUNT_PY = ROOT / "ops" / "_count_employee_profile_fill.py"


def _ssh() -> tuple[str, str]:
    lines = [
        ln.strip()
        for ln in (ROOT / "ops" / "vps-root.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    return lines[0], lines[1]


def _find_xlsx() -> Path:
    matches = sorted(
        p
        for p in list(XLSX_DIR.glob("*bổ sung*.xlsx")) + list(XLSX_DIR.glob("*bo sung*.xlsx"))
        if not p.name.startswith("~$")
    )
    if not matches:
        raise SystemExit(f"Không thấy file Thông tin bổ sung .xlsx trong {XLSX_DIR}")
    return matches[0]


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
    if not COUNT_PY.is_file():
        raise SystemExit(f"Không thấy {COUNT_PY}")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(xlsx, arcname="bo_sung.xlsx")
        tar.add(COUNT_PY, arcname="count_fill.py")
    payload = buf.getvalue()
    print(f"Gói {xlsx.name} ({len(payload) / 1e3:.0f} KB)")

    ip, pw = _ssh()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", password=pw, timeout=60)
    try:
        with SCPClient(client.get_transport()) as scp:
            scp.putfo(io.BytesIO(payload), "/tmp/bo_sung.tar.gz")
        _exec(client, "rm -rf /tmp/bo_sung && mkdir -p /tmp/bo_sung && tar -xzf /tmp/bo_sung.tar.gz -C /tmp/bo_sung")
        _exec(client, "docker cp /tmp/bo_sung/bo_sung.xlsx djhrm-api:/tmp/bo_sung.xlsx")
        _exec(client, "docker cp /tmp/bo_sung/count_fill.py djhrm-api:/tmp/count_fill.py")
        _exec(
            client,
            "docker exec djhrm-api python -m app.scripts.import_thong_tin_bo_sung --xlsx /tmp/bo_sung.xlsx",
            timeout=600,
        )
        _exec(client, "docker exec -w /app -e PYTHONPATH=/app djhrm-api python /tmp/count_fill.py")
        _exec(client, "rm -rf /tmp/bo_sung /tmp/bo_sung.tar.gz")
    finally:
        client.close()
    print("XONG — F5 Portal → Nhân sự, kiểm tra phụ cấp / quốc tịch / dân tộc / tôn giáo / trình độ.")


if __name__ == "__main__":
    main()
