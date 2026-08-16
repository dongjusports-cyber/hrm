#!/usr/bin/env bash
# DJ HRM — Backup PostgreSQL (Linux/macOS)
set -euo pipefail

CONTAINER="${POSTGRES_CONTAINER:-djhrm-postgres}"
PGUSER="${POSTGRES_USER:-djhrm}"
PGDB="${POSTGRES_DB:-djhrm}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/djhrm_${STAMP}.dump"

echo "COSMOS AI: đang backup ${PGDB} từ container ${CONTAINER} ..."
docker exec -t "$CONTAINER" pg_dump -U "$PGUSER" -d "$PGDB" -Fc -f /tmp/djhrm_backup.dump
docker cp "${CONTAINER}:/tmp/djhrm_backup.dump" "$OUT"
docker exec -t "$CONTAINER" rm -f /tmp/djhrm_backup.dump >/dev/null

find "$BACKUP_DIR" -name 'djhrm_*.dump' -type f -mtime +"$KEEP_DAYS" -print -delete || true

echo "Xong: $OUT"
if [[ ! -s "$OUT" ]] || [[ "$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT")" -lt 1000 ]]; then
  echo "COSMOS AI: file backup quá nhỏ — kiểm tra pg_dump." >&2
fi

OFFSITE="${BACKUP_OFFSITE_DIR:-/var/backups/djhrm}"
if mkdir -p "$OFFSITE" 2>/dev/null; then
  cp -f "$OUT" "$OFFSITE/"
  echo "Bản sao: ${OFFSITE}/$(basename "$OUT")"
fi

echo "Giữ tối đa ${KEEP_DAYS} ngày (RPO mục tiêu 24h)."
echo "Keo ve may nha: python ops/pull_vps_backup.py"
