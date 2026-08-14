import paramiko
from pathlib import Path

lines = [
    l.strip()
    for l in Path(__file__).resolve().parents[1].joinpath("ops/vps-root.txt").read_text().splitlines()
    if l.strip() and not l.startswith("#")
]
ip, pw = lines[0], lines[1]
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(ip, username="root", password=pw, timeout=30)
cmds = [
    'docker ps --format "{{.Names}} {{.Status}}"',
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/health; echo",
    "curl -sk -o /dev/null -w '%{http_code}' https://hrm.dongju-v.com/health; echo",
    "docker compose -f /opt/dj-hrm/docker-compose.prod.yml --env-file /opt/dj-hrm/.env.prod exec -T api python -c 'from app.core.database import SessionLocal; from app.modules.mdm.models import Employee; db=SessionLocal(); print(db.query(Employee).count()); db.close()' 2>&1 || echo API_FAIL",
]
for cmd in cmds:
    print(">", cmd[:70])
    _, o, e = c.exec_command(cmd, timeout=120)
    print(o.read().decode("utf-8", "replace"))
    err = e.read().decode("utf-8", "replace")
    if err:
        print("ERR:", err)
c.close()
