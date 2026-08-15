#!/usr/bin/env bash
# Chay TREN VPS sau git pull — deploy code moi (giu .env.prod + DB)
set -euo pipefail
cd /opt/dj-hrm
echo "== git pull =="
git pull --ff-only || git pull
echo "== deploy =="
./ops/deploy.sh --ssl --skip-backup
echo "== health =="
curl -fsSk "https://${DOMAIN:-hrm.dongju-v.com}/health" | head -c 200 || true
echo
echo "DEPLOY XONG $(date -Iseconds)"
