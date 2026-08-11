#!/usr/bin/env bash
# Đăng ký cron backup hằng ngày 02:00 (VPS Linux) — 10.9 / 12§12.4
#   chmod +x ops/register-backup-cron.sh
#   ./ops/register-backup-cron.sh
# Gỡ: ./ops/register-backup-cron.sh --unregister
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="# DJHRM-DailyBackup"
LINE="0 2 * * * cd ${ROOT} && ./ops/backup.sh >> ${ROOT}/backups/backup-task.log 2>&1 ${MARKER}"

mkdir -p "${ROOT}/backups"
chmod +x "${ROOT}/ops/backup.sh" "${ROOT}/ops/restore.sh" || true

if [[ "${1:-}" == "--unregister" ]]; then
  (crontab -l 2>/dev/null | grep -v "${MARKER}" || true) | crontab -
  echo "Đã gỡ cron DJ HRM backup."
  exit 0
fi

(crontab -l 2>/dev/null | grep -v "${MARKER}" || true; echo "${LINE}") | crontab -
echo "OK — cron backup 02:00 mỗi ngày."
echo "Log: ${ROOT}/backups/backup-task.log"
crontab -l | grep "${MARKER}" || true
