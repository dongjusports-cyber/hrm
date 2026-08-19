#!/usr/bin/env python3
"""Kiem tra VPS da ket noi GitHub bang Deploy Key chua."""
from __future__ import annotations

from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CRED = ROOT / "ops" / "vps-root.txt"

TEST = r"""
set -e
ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true
chmod 644 /root/.ssh/known_hosts 2>/dev/null || true
echo "== ssh -T github =="
ssh -T git@github.com 2>&1 || true
echo "== git ls-remote (5 dong dau) =="
cd /opt/dj-hrm
git remote -v
git ls-remote origin HEAD 2>&1 | head -5
"""


def main() -> int:
    lines = [
        l.strip()
        for l in CRED.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]
    ip, pw = lines[0], lines[1]
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ip, username="root", password=pw, timeout=60)
    _, o, e = c.exec_command(TEST, timeout=120)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    c.close()
    print(out)
    if err.strip():
        print(err)
    ok = "Hi " in out or "successfully authenticated" in out.lower()
    if "git ls-remote" in out and "fatal" not in out.split("git ls-remote")[-1]:
        ok = True
    if ok:
        print("\nOK — VPS co the git pull tu GitHub.")
        return 0
    print("\nCHUA OK — hay them Deploy Key tren GitHub (Thien-Admin\\01-THEM-DEPLOY-KEY.bat).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
