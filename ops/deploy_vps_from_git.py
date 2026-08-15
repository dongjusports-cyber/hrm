#!/usr/bin/env python3
"""Tu may Windows: git pull tren VPS + deploy (sau khi da push GitHub)."""
from __future__ import annotations

from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
lines = [
    l.strip()
    for l in (ROOT / "ops" / "vps-root.txt").read_text().splitlines()
    if l.strip() and not l.startswith("#")
]
ip, pw = lines[0], lines[1]

sh = (ROOT / "ops" / "deploy_from_git.sh").read_bytes().replace(b"\r\n", b"\n")

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(ip, username="root", password=pw, timeout=60)
with SCPClient(c.get_transport()) as scp:
    scp.putfo(__import__("io").BytesIO(sh), "/root/deploy_from_git.sh")
_, o, e = c.exec_command("bash /root/deploy_from_git.sh", timeout=900)
print(o.read().decode("utf-8", errors="replace"))
err = e.read().decode("utf-8", errors="replace")
if err.strip():
    print(err)
c.close()
