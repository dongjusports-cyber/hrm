#!/usr/bin/env python3
"""Tu may Windows: mo khoa + dat lai pass admin/hr.demo tren VPS (khong can hoi AI)."""
from __future__ import annotations

from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
CRED = ROOT / "ops" / "vps-root.txt"
SCRIPT = ROOT / "ops" / "reset_portal_passwords.sh"


def main() -> None:
    if not CRED.is_file():
        print("Thieu ops/vps-root.txt (IP + pass root VPS)")
        raise SystemExit(1)
    lines = [
        l.strip()
        for l in CRED.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]
    ip, pw = lines[0], lines[1]
    sh = SCRIPT.read_bytes().replace(b"\r\n", b"\n")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username="root", password=pw, timeout=60)
    with SCPClient(client.get_transport()) as scp:
        scp.putfo(__import__("io").BytesIO(sh), "/root/reset_portal_passwords.sh")
    _, out, err = client.exec_command("bash /root/reset_portal_passwords.sh", timeout=120)
    print(out.read().decode("utf-8", errors="replace"))
    e = err.read().decode("utf-8", errors="replace")
    if e and "error reading bcrypt" not in e:
        print(e)
    client.close()
    print()
    print("=== DANG NHAP LAI ===")
    print("  admin:    Thanhthien0918283825@")
    print("  hr.demo:  demo123456")
    print("  https://hrm.dongju-v.com")


if __name__ == "__main__":
    main()
