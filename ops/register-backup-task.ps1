# Đăng ký Task Scheduler: backup DJ HRM mỗi ngày 02:00 (10.9 / 12§12.4)
# Chạy PowerShell (Admin khuyến nghị):
#   cd C:\DATA\HRM\dj-hrm\dj-hrm
#   .\ops\register-backup-task.ps1
# Gỡ: .\ops\register-backup-task.ps1 -Unregister

param(
  [switch]$Unregister,
  [string]$TaskName = "DJHRM-DailyBackup",
  [string]$Time = "02:00"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackupScript = Join-Path $RepoRoot "ops\backup.ps1"
$LogDir = Join-Path $RepoRoot "backups"
$LogFile = Join-Path $LogDir "backup-task.log"

if (-not (Test-Path $BackupScript)) {
  throw "COSMOS AI: không thấy $BackupScript"
}

if ($Unregister) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Đã gỡ task '$TaskName'."
  exit 0
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Wrapper: cd repo rồi gọi backup, ghi log
$wrapper = Join-Path $env:TEMP "djhrm-backup-wrapper.ps1"
@"
`$ErrorActionPreference = 'Stop'
Set-Location '$RepoRoot'
`$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -Path '$LogFile' -Value "[`$stamp] Bắt đầu backup..."
try {
  & '$BackupScript' *>> '$LogFile'
  Add-Content -Path '$LogFile' -Value "[`$stamp] Xong."
} catch {
  Add-Content -Path '$LogFile' -Value "[`$stamp] LỖI: `$_"
  exit 1
}
"@ | Set-Content -Path $wrapper -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapper`""
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
  -Description "DJ HRM pg_dump hằng ngày (RPO 24h, giữ 30 ngày)" | Out-Null

Write-Host "OK — Task '$TaskName' chạy mỗi ngày lúc $Time."
Write-Host "Repo: $RepoRoot"
Write-Host "Log:  $LogFile"
Write-Host "Thử ngay: Start-ScheduledTask -TaskName '$TaskName'"
