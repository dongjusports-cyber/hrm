#!/usr/bin/env bash
set -e
cd /opt/dj-hrm
if [[ -f /root/djhrm_local_latest.dump ]]; then
  echo "RESTORE..."
  docker cp /root/djhrm_local_latest.dump djhrm-postgres:/tmp/djhrm_restore.dump
  docker exec djhrm-postgres pg_restore -U djhrm -d djhrm --clean --if-exists /tmp/djhrm_restore.dump || true
  docker exec djhrm-postgres rm -f /tmp/djhrm_restore.dump
  docker compose -f docker-compose.prod.yml --env-file .env.prod restart api
  sleep 8
fi
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T api python -c "
from app.core.database import SessionLocal
from app.modules.mdm.models import Employee, Department, Team
db = SessionLocal()
print('emps', db.query(Employee).count())
print('depts', db.query(Department).count())
print('teams', db.query(Team).count())
db.close()
"
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T api curl -s http://127.0.0.1:8000/health
echo
