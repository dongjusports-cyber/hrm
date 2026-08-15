#!/usr/bin/env bash
# Mo khoa + dat lai mat khau admin / hr.demo tren VPS production.
set -euo pipefail
cd /opt/dj-hrm

docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T api python <<'PY'
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.core.models import User

ADMIN_PASS = "Thanhthien0918283825@"
HR_PASS = "demo123456"

db = SessionLocal()
try:
    changed = []
    for username, new_pass, label in (
        ("admin", ADMIN_PASS, "admin"),
        ("hr.demo", HR_PASS, "hr.demo"),
    ):
        user = db.query(User).filter(User.username == username).one_or_none()
        if user is None:
            print(f"SKIP: khong tim thay {username}")
            continue
        user.password_hash = hash_password(new_pass)
        user.is_locked = False
        user.failed_attempts = 0
        user.failed_login_count = 0
        user.is_active = True
        user.must_change_password = False
        changed.append(label)
    db.commit()
    print("OK — da mo khoa va dat lai mat khau:", ", ".join(changed))
finally:
    db.close()
PY

echo "XONG reset portal $(date -Iseconds)"
