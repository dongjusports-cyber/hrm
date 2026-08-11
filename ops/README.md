# Ops — Backup / Restore / Deploy (không cần IT sâu)

Theo Hiến pháp `12`§12.4: `pg_dump` hằng ngày, giữ 30 ngày, RPO 24h / RTO ~4h.

Deploy VPS + SSL (P6.1): xem [`DEPLOY_VPS.md`](./DEPLOY_VPS.md).

```bash
./ops/preflight_prod.sh .env.prod
./ops/deploy.sh --seed          # lần đầu
./ops/deploy.sh --ssl           # HTTPS Let's Encrypt
```

## Windows (PowerShell)

```powershell
# Backup một lần
.\ops\backup.ps1

# Đăng ký tự động mỗi ngày 02:00 (Go-live 10.9)
.\ops\register-backup-task.ps1
# Gỡ: .\ops\register-backup-task.ps1 -Unregister
# Thử: Start-ScheduledTask -TaskName DJHRM-DailyBackup

# Restore (CẨN THẬN — ghi đè DB)
.\ops\restore.ps1 -BackupFile .\backups\djhrm_20260809_120000.dump
```

## Linux / macOS / Git Bash

```bash
chmod +x ops/backup.sh ops/restore.sh ops/register-backup-cron.sh
./ops/backup.sh
./ops/register-backup-cron.sh          # cron 02:00
# Gỡ: ./ops/register-backup-cron.sh --unregister
./ops/restore.sh ./backups/djhrm_YYYYMMDD_HHMMSS.dump
```

## Biến môi trường (tuỳ chọn)

| Biến | Mặc định |
|------|----------|
| `POSTGRES_CONTAINER` | `djhrm-postgres` |
| `POSTGRES_USER` | `djhrm` |
| `POSTGRES_DB` | `djhrm` |
| `BACKUP_DIR` | `./backups` |
| `BACKUP_KEEP_DAYS` | `30` |

Script dùng `docker exec` vào container Postgres local. Trước khi restore: dừng API nếu đang ghi dữ liệu.
