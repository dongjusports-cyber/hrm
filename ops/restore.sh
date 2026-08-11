#!/usr/bin/env bash
# DJ HRM — Restore PostgreSQL (Linux/macOS)
# CẨN THẬN: ghi đè database.
set -euo pipefail

BACKUP_FILE="${1:-}"
CONTAINER="${POSTGRES_CONTAINER:-djhrm-postgres}"
PGUSER="${POSTGRES_USER:-djhrm}"
PGDB="${POSTGRES_DB:-djhrm}"

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Dùng: ./ops/restore.sh ./backups/djhrm_YYYYMMDD_HHMMSS.dump"
  exit 1
fi

echo "CẢNH BÁO: sẽ ghi đè database ${PGDB}."
read -r -p "Gõ YES để tiếp tục: " OK
if [[ "$OK" != "YES" ]]; then
  echo "Đã hủy."
  exit 1
fi

docker cp "$BACKUP_FILE" "${CONTAINER}:/tmp/djhrm_restore.dump"
docker exec -t "$CONTAINER" pg_restore -U "$PGUSER" -d "$PGDB" --clean --if-exists /tmp/djhrm_restore.dump || true
docker exec -t "$CONTAINER" rm -f /tmp/djhrm_restore.dump >/dev/null
echo "Restore xong. Kiểm tra /health. Restart API nếu cần: docker compose restart api"
