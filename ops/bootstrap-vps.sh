#!/usr/bin/env bash
# Chạy TRÊN VPS (root) — cài Docker, deploy dj-hrm, restore DB từ backup local.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/dj-hrm}"
ENV_SRC="${ENV_SRC:-/root/djhrm-vps.env}"
DUMP_SRC="${DUMP_SRC:-/root/djhrm_local_latest.dump}"
REPO_URL="${REPO_URL:-https://github.com/nguyenthiendongju-hub/dj-.git}"

export DEBIAN_FRONTEND=noninteractive

echo "== DJ HRM bootstrap VPS =="

if [[ ! -f "$ENV_SRC" ]]; then
  echo "Thieu $ENV_SRC — chay SETUP_VPS.ps1 tu may Windows truoc." >&2
  exit 1
fi

echo "-> Cap nhat he thong + Docker..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl git ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker 2>/dev/null || true

if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y -qq docker-compose-plugin || true
fi

echo "-> Firewall (22, 80, 443)..."
ufw --force reset >/dev/null 2>&1 || true
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable || ufw --force enable

echo "-> Clone repo..."
mkdir -p "$(dirname "$INSTALL_DIR")"
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
git pull --ff-only || git pull || true

cp "$ENV_SRC" .env.prod
chmod +x ops/*.sh 2>/dev/null || true

echo "-> Deploy (migrate, chua seed)..."
./ops/deploy.sh --skip-backup

if [[ -f "$DUMP_SRC" ]]; then
  echo "-> Restore DB tu backup local (359 NV)..."
  docker cp "$DUMP_SRC" djhrm-postgres:/tmp/djhrm_restore.dump
  docker exec -t djhrm-postgres pg_restore -U djhrm -d djhrm --clean --if-exists /tmp/djhrm_restore.dump 2>/dev/null || true
  docker exec -t djhrm-postgres rm -f /tmp/djhrm_restore.dump
  docker compose -f docker-compose.prod.yml --env-file .env.prod restart api
  echo "   Restore xong."
else
  echo "-> Khong thay dump — chay seed + NAP_NV tren VPS sau."
  ./ops/deploy.sh --seed --skip-backup
fi

# shellcheck disable=SC1091
set -a
source .env.prod
set +a

if [[ -n "${DOMAIN:-}" && "${DOMAIN}" != "hrm.example.com" ]]; then
  echo "-> Thu bat SSL (${DOMAIN})..."
  if ./ops/deploy.sh --ssl --skip-backup; then
    echo "   HTTPS OK."
  else
    echo "   SSL chua duoc — kiem tra DNS A record tro ve IP VPS roi chay: ./ops/deploy.sh --ssl"
  fi
fi

HEALTH_PORT="${WEB_PUBLISH_PORT:-8080}"
if curl -fsS "http://127.0.0.1:${HEALTH_PORT}/health" >/dev/null 2>&1; then
  echo "OK — http://127.0.0.1:${HEALTH_PORT}/health"
elif [[ -n "${DOMAIN:-}" ]] && curl -fkS "https://${DOMAIN}/health" >/dev/null 2>&1; then
  echo "OK — https://${DOMAIN}/health"
else
  echo "Health chua OK — xem log: docker compose -f docker-compose.prod.yml logs --tail=50 api"
fi

echo ""
echo "BOOTSTRAP XONG."
echo "  Portal: https://${DOMAIN:-IP_VPS} hoac :${HEALTH_PORT}"
echo "  Agent .122: DJ_API_BASE_URL=https://${DOMAIN:-IP_VPS}"
