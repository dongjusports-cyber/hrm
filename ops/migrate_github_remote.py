#!/usr/bin/env python3
"""Doi remote GitHub (may .123 + VPS) sang repo moi trong ops/github.repo."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops"))
from github_repo import DEPLOY_KEYS_URL, HTTPS, REPO_HOME, SSH  # noqa: E402

CRED = ROOT / "ops" / "vps-root.txt"


def local_remote() -> None:
    print("== May .123: git remote ==")
    subprocess.run(["git", "remote", "set-url", "origin", HTTPS], cwd=ROOT, check=True)
    r = subprocess.run(["git", "remote", "-v"], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout)


def vps_remote() -> None:
    lines = [
        l.strip()
        for l in CRED.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]
    ip, pw = lines[0], lines[1]
    cmd = f"""
cd /opt/dj-hrm 2>/dev/null || exit 0
git remote set-url origin {SSH}
git remote -v
"""
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ip, username="root", password=pw, timeout=60)
    _, o, e = c.exec_command(cmd, timeout=60)
    print("== VPS: git remote ==")
    print(o.read().decode("utf-8", errors="replace"))
    err = e.read().decode("utf-8", errors="replace")
    if err.strip():
        print(err)
    c.close()


def main() -> None:
    print(f"Repo moi: {REPO_HOME}\n")
    local_remote()
    print()
    vps_remote()
    print()
    print("Deploy keys:", DEPLOY_KEYS_URL)
    print("Tiep theo: Thien-Admin\\00-PUSH-GITHUB-MOI.bat (lan dau)")
    print("           Thien-Admin\\01-THEM-DEPLOY-KEY.bat")


if __name__ == "__main__":
    main()
