#!/usr/bin/env python3
"""Nạp ảnh chân dung {MSNV}.jpg lên VPS, gắn đúng mã nhân viên.

Không xóa NV, không sửa ngày sinh/lương. Chạy từ máy .123:
  python ops/fill_vps_employee_photos.py
"""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
PHOTO_CANDIDATES = [
    ROOT / "HIEN_PHAP" / "Thông tin danh sách nhân viên" / "trich_xuat_140826" / "photos",
    ROOT / "Dữ liệu nhân viên" / "Thông tin danh sách nhân viên" / "trich_xuat_140826" / "photos",
]


def _photo_dir() -> Path:
    for path in PHOTO_CANDIDATES:
        if path.is_dir() and any(path.glob("*.jpg")):
            return path
    raise SystemExit("Không thấy photos/{MSNV}.jpg trong trich_xuat_140826")


def _ssh() -> tuple[str, str]:
    lines = [
        ln.strip()
        for ln in (ROOT / "ops" / "vps-root.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    return lines[0], lines[1]


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
    photos = _photo_dir()
    files = sorted(p for p in photos.glob("*.jpg") if p.stat().st_size >= 500)
    if not files:
        raise SystemExit(f"Không có file jpg trong {photos}")
    print(f"Nguồn {photos} — {len(files)} ảnh")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in files:
            tar.add(path, arcname=f"photos/{path.name}")
    payload = buf.getvalue()
    print(f"Gói {len(payload) / 1e6:.1f} MB")

    ip, pw = _ssh()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", password=pw, timeout=60)
    try:
        with SCPClient(client.get_transport()) as scp:
            scp.putfo(io.BytesIO(payload), "/tmp/nv_photos.tar.gz")
        _exec(client, "rm -rf /tmp/nv_photos && mkdir -p /tmp/nv_photos && tar -xzf /tmp/nv_photos.tar.gz -C /tmp/nv_photos")
        _exec(client, "docker cp /tmp/nv_photos/photos djhrm-api:/tmp/photos")
        _exec(
            client,
            "docker exec djhrm-api python -m app.scripts.attach_photos_by_msnv /tmp/photos",
            timeout=180,
        )
        _exec(client, "rm -rf /tmp/nv_photos /tmp/nv_photos.tar.gz")
    finally:
        client.close()
    print("XONG — F5 Portal → Nhân sự, mở vài MSNV xem ảnh chân dung.")


if __name__ == "__main__":
    main()
