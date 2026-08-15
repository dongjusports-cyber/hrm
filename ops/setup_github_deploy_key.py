#!/usr/bin/env python3
"""Tao Deploy Key tren VPS + huong dan add GitHub."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops"))
from github_repo import SSH  # noqa: E402

CRED = ROOT / "ops" / "vps-root.txt"
KEY_PATH = "/root/.ssh/github_djhrm"
PUB_PATH = f"{KEY_PATH}.pub"

SETUP = rf"""
set -e
mkdir -p /root/.ssh
chmod 700 /root/.ssh
if [ ! -f {KEY_PATH} ]; then
  ssh-keygen -t ed25519 -C "dj-hrm-vps-deploy" -f {KEY_PATH} -N ""
fi
cat > /root/.ssh/config <<'CFG'
Host github.com
  HostName github.com
  User git
  IdentityFile /root/.ssh/github_djhrm
  IdentitiesOnly yes
CFG
chmod 600 /root/.ssh/config /root/.ssh/github_djhrm
chmod 644 {PUB_PATH}
ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true
chmod 644 /root/.ssh/known_hosts 2>/dev/null || true
echo "=== PUBLIC KEY (dán lên GitHub Deploy keys) ==="
cat {PUB_PATH}
echo "=== TEST (sau khi add key) ==="
ssh -T git@github.com 2>&1 || true
cd /opt/dj-hrm 2>/dev/null && git remote set-url origin {SSH} && git remote -v || true
"""


def main() -> None:
    lines = [
        l.strip()
        for l in CRED.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]
    ip, pw = lines[0], lines[1]
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ip, username="root", password=pw, timeout=60)
    _, o, e = c.exec_command(SETUP, timeout=120)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    c.close()
    print(out)
    if err.strip():
        print(err)
    # Luu public key local
    if "PUBLIC KEY" in out:
        for line in out.splitlines():
            if line.startswith("ssh-ed25519"):
                (ROOT / "ops" / "github_deploy_key.pub").write_text(line + "\n", encoding="utf-8")
                print("\nDa luu: ops/github_deploy_key.pub")


if __name__ == "__main__":
    main()
