#!/usr/bin/env bash
# P6.1 — Deploy DJ HRM lên VPS (Docker Compose + migrate)
# Chạy trên VPS từ thư mục gốc repo:
#   chmod +x ops/deploy.sh
#   ./ops/deploy.sh              # HTTP :8080 (chưa SSL)
#   ./ops/deploy.sh --ssl        # Caddy 80/443 + Let's Encrypt
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.prod}"
USE_SSL=0
DO_SEED=0
SKIP_BACKUP=0

for arg in "$@"; do
  case "$arg" in
    --ssl) USE_SSL=1 ;;
    --seed) DO_SEED=1 ;;
    --skip-backup) SKIP_BACKUP=1 ;;
    -h|--help)
      echo "Usage: $0 [--ssl] [--seed] [--skip-backup]"
      exit 0
      ;;
    *)
      echo "COSMOS AI: tham số không hợp lệ: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "COSMOS AI: thiếu $ENV_FILE — copy từ .env.prod.example rồi điền secret." >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

: "${APP_ENV:=production}"
: "${JWT_SECRET:?Thiếu JWT_SECRET}"
: "${AGENT_TOKEN:?Thiếu AGENT_TOKEN}"
: "${POSTGRES_PASSWORD:?Thiếu POSTGRES_PASSWORD}"

if [[ "$JWT_SECRET" == "change_me_to_a_long_random_string" ]] || [[ ${#JWT_SECRET} -lt 24 ]]; then
  echo "COSMOS AI: JWT_SECRET còn yếu — đổi trước khi deploy." >&2
  exit 1
fi
if [[ "$AGENT_TOKEN" == "change_me_agent_token" ]]; then
  echo "COSMOS AI: AGENT_TOKEN còn mặc định — đổi trước khi deploy." >&2
  exit 1
fi
if [[ "${CORS_ORIGINS:-}" == *"*"* ]]; then
  echo "COSMOS AI: CORS_ORIGINS không được dùng * trên production." >&2
  exit 1
fi

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE")
if [[ "$USE_SSL" -eq 1 ]]; then
  : "${DOMAIN:?--ssl cần DOMAIN trong $ENV_FILE}"
  : "${CADDY_EMAIL:?--ssl cần CADDY_EMAIL trong $ENV_FILE}"
  COMPOSE=(docker compose -f docker-compose.prod.yml -f docker-compose.ssl.yml --env-file "$ENV_FILE")
  echo "→ Deploy HTTPS domain=${DOMAIN}"
else
  echo "→ Deploy HTTP (web :${WEB_PUBLISH_PORT:-8080}) — gắn SSL bằng: $0 --ssl"
fi

if [[ "$SKIP_BACKUP" -eq 0 ]] && docker ps --format '{{.Names}}' | grep -qx 'djhrm-postgres'; then
  echo "→ Backup trước deploy..."
  bash ./ops/backup.sh || echo "COSMOS AI: backup bỏ qua (lần đầu chưa có DB)."
fi

echo "→ Build & up..."
"${COMPOSE[@]}" up -d --build

echo "→ Chờ Postgres healthy..."
for i in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T postgres pg_isready -U "${POSTGRES_USER:-djhrm}" -d "${POSTGRES_DB:-djhrm}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [[ "$i" -eq 60 ]]; then
    echo "COSMOS AI: Postgres chưa sẵn sàng." >&2
    exit 1
  fi
done

echo "→ Alembic migrate..."
"${COMPOSE[@]}" exec -T api alembic upgrade head

if [[ "$DO_SEED" -eq 1 ]]; then
  echo "→ Seed Admin / demo..."
  "${COMPOSE[@]}" exec -T api python -m app.scripts.seed
fi

echo "→ Health..."
if [[ "$USE_SSL" -eq 1 ]]; then
  HEALTH_URL="https://${DOMAIN}/health"
else
  HEALTH_URL="http://127.0.0.1:${WEB_PUBLISH_PORT:-8080}/health"
fi
sleep 3
if curl -fsS "$HEALTH_URL" >/dev/null 2>&1 || curl -fkS "$HEALTH_URL" >/dev/null 2>&1; then
  echo "OK — $HEALTH_URL"
else
  echo "COSMOS AI: health chưa trả OK — kiểm tra: ${COMPOSE[*]} logs --tail=80"
  "${COMPOSE[@]}" ps
  exit 1
fi

echo "Deploy xong. Agent nhà máy: DJ_API_BASE_URL=https://${DOMAIN:-VPS} + DJ_AGENT_REQUIRE_HTTPS=1"
