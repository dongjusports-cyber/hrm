#!/usr/bin/env python3
"""Setup DJ HRM on VPS from Windows (SSH + SCP). Reads ops/vps-root.txt."""
from __future__ import annotations

import secrets
import string
import sys
from pathlib import Path

import paramiko
from scp import SCPClient

ROOT = Path(__file__).resolve().parents[1]
CRED_FILE = ROOT / "ops" / "vps-root.txt"


def _secret(n: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _read_creds() -> tuple[str, str, str, str]:
    if not CRED_FILE.is_file():
        print(f"Thieu {CRED_FILE} — xem ops/vps-root.txt.example")
        sys.exit(1)
    lines = [
        ln.strip()
        for ln in CRED_FILE.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if len(lines) < 2:
        print("vps-root.txt can IP + mat khau root")
        sys.exit(1)
    ip, passwd = lines[0], lines[1]
    domain = lines[2] if len(lines) > 2 else "hrm.dongju-v.com"
    agent = lines[3] if len(lines) > 3 else ""
    if not agent:
        print("vps-root.txt can dong 4: AGENT_TOKEN (trung .env.prod)")
        sys.exit(1)
    return ip, passwd, domain, agent


def _env_prod(domain: str, agent: str, admin_pass: str, pg_pass: str, jwt: str) -> str:
    return f"""APP_ENV=production
APP_NAME=DJ-HRM
POSTGRES_USER=djhrm
POSTGRES_PASSWORD={pg_pass}
POSTGRES_DB=djhrm
JWT_SECRET={jwt}
JWT_ACCESS_HOURS=8
JWT_REFRESH_DAYS=7
CORS_ORIGINS=https://{domain}
TRUSTED_HOSTS={domain},localhost
AGENT_TOKEN={agent}
ADMIN_USERNAME=admin
ADMIN_PASSWORD={admin_pass}
ADMIN_FULL_NAME=Nguyen_Thanh_Thien
WEB_PUBLISH_PORT=8080
LOG_DIR=/var/log/djhrm
DOCS_ENABLED=false
DOMAIN={domain}
CADDY_EMAIL=admin@dongju-v.com
"""


def main() -> None:
    ip, passwd, domain, agent = _read_creds()
    admin_pass = _secret(16)
    pg_pass = _secret(24)
    jwt = _secret(40)

    env_local = ROOT / "ops" / "djhrm-vps.env"
    env_local.write_text(_env_prod(domain, agent, admin_pass, pg_pass, jwt), encoding="utf-8", newline="\n")

    print(f"== SETUP VPS {ip} ==")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username="root", password=passwd, timeout=60, look_for_keys=False, allow_agent=False)
    except Exception as exc:
        print(f"SSH that bai: {exc}")
        print("Kiem tra mat khau trong vps-root.txt (co the da doi sau khi mua)")
        sys.exit(1)

    bootstrap = (ROOT / "ops" / "bootstrap-vps.sh").read_bytes().replace(b"\r\n", b"\n")
    bootstrap_lf = ROOT / "ops" / ".bootstrap-vps-lf.sh"
    bootstrap_lf.write_bytes(bootstrap)

    with SCPClient(client.get_transport()) as scp:
        scp.put(str(bootstrap_lf), "/root/bootstrap-vps.sh")
        scp.put(str(env_local), "/root/djhrm-vps.env")
        dump = ROOT / "backups" / "djhrm_local_latest.dump"
        if dump.is_file():
            kb = dump.stat().st_size // 1024
            print(f"-> Upload backup DB ({kb} KB)...")
            scp.put(str(dump), "/root/djhrm_local_latest.dump")
        else:
            print("Khong thay backup dump — VPS se seed demo.")

    print("-> Chay bootstrap (5-15 phut)...")
    stdin, stdout, stderr = client.exec_command(
        "chmod +x /root/bootstrap-vps.sh && bash /root/bootstrap-vps.sh",
        timeout=900,
    )
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    if err:
        print(err)
    client.close()

    cred_out = ROOT / "ops" / "vps-admin-credentials.txt"
    cred_out.write_text(
        f"VPS IP: {ip}\nDomain: https://{domain}\nAdmin: admin / {admin_pass}\n"
        f"AGENT_TOKEN: {agent}\n",
        encoding="utf-8",
    )

    if code != 0:
        print(f"Bootstrap loi (exit {code})")
        sys.exit(code)

    print("\n=== XONG ===")
    print(f"  URL:   https://{domain}  (hoac http://{ip}:8080)")
    print(f"  Admin: admin / {admin_pass}")
    print(f"  Da luu: ops/vps-admin-credentials.txt")


if __name__ == "__main__":
    main()
