# DJ HRM — Restore PostgreSQL (Windows)
# CẨN THẬN: ghi đè database hiện tại.
# .\ops\restore.ps1 -BackupFile .\backups\djhrm_YYYYMMDD_HHMMSS.dump

param(
  [Parameter(Mandatory = $true)]
  [string]$BackupFile
)

$ErrorActionPreference = "Stop"
$Container = if ($env:POSTGRES_CONTAINER) { $env:POSTGRES_CONTAINER } else { "djhrm-postgres" }
$PgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "djhrm" }
$PgDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "djhrm" }

if (-not (Test-Path $BackupFile)) {
  throw "Không tìm thấy file backup: $BackupFile"
}

Write-Host "CẢNH BÁO: sẽ ghi đè database $PgDb."
$ok = Read-Host "Gõ YES để tiếp tục"
if ($ok -ne "YES") {
  Write-Host "Đã hủy."
  exit 1
}

Write-Host "Copy dump vào container..."
docker cp $BackupFile "${Container}:/tmp/djhrm_restore.dump"
Write-Host "Đang restore (có thể mất vài phút)..."
docker exec -t $Container pg_restore -U $PgUser -d $PgDb --clean --if-exists "/tmp/djhrm_restore.dump"
# pg_restore có thể trả code != 0 với warning — vẫn kiểm tra sơ
docker exec -t $Container rm -f /tmp/djhrm_restore.dump | Out-Null
Write-Host "Restore xong. Kiểm tra Web /health và đăng nhập Admin."
Write-Host "Nếu API đang chạy: docker compose restart api"
