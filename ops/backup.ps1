# DJ HRM — Backup PostgreSQL (Windows)
# Chạy từ thư mục gốc repo: .\ops\backup.ps1

$ErrorActionPreference = "Stop"
$Container = if ($env:POSTGRES_CONTAINER) { $env:POSTGRES_CONTAINER } else { "djhrm-postgres" }
$PgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "djhrm" }
$PgDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "djhrm" }
$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { Join-Path (Get-Location) "backups" }
$KeepDays = if ($env:BACKUP_KEEP_DAYS) { [int]$env:BACKUP_KEEP_DAYS } else { 30 }

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $BackupDir "djhrm_$stamp.dump"

Write-Host "COSMOS AI: đang backup $PgDb từ container $Container ..."
docker exec -t $Container pg_dump -U $PgUser -d $PgDb -Fc -f "/tmp/djhrm_backup.dump"
if ($LASTEXITCODE -ne 0) { throw "pg_dump thất bại. Kiểm tra docker compose ps." }

docker cp "${Container}:/tmp/djhrm_backup.dump" $outFile
docker exec -t $Container rm -f /tmp/djhrm_backup.dump | Out-Null

Get-ChildItem $BackupDir -Filter "djhrm_*.dump" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
  ForEach-Object {
    Write-Host "Xóa backup cũ: $($_.Name)"
    Remove-Item $_.FullName -Force
  }

Write-Host "Xong: $outFile"
Write-Host "Giữ tối đa $KeepDays ngày (RPO mục tiêu 24h)."
