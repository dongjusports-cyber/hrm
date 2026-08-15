#!/usr/bin/env bash
# Chay TREN VPS sau git pull — deploy code moi (giu .env.prod + DB)
set -euo pipefail
cd /opt/dj-hrm
echo "== git pull =="
# Bo thay doi local le tren repo (vd. bootstrap-vps.sh) — giu .env.prod (gitignore)
git fetch origin main
if ! git diff --quiet HEAD 2>/dev/null; then
  echo "(stash thay doi local truoc khi pull)"
  git stash push -m "pre-deploy-$(date -Iseconds)" -- ops/ 2>/dev/null || git checkout -- ops/ 2>/dev/null || true
fi
git pull --ff-only origin main || git pull origin main
echo "== deploy =="
./ops/deploy.sh --ssl --skip-backup
echo "== health =="
curl -fsSk "https://${DOMAIN:-hrm.dongju-v.com}/health" | head -c 200 || true
echo
echo "DEPLOY XONG $(date -Iseconds)"
