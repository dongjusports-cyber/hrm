$ErrorActionPreference = "Continue"
$log = "D:\HRM\dj-hrm\ops\native-deps-install.log"
function Log($m){ "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }
Log "START native deps"
winget install -e --id PostgreSQL.PostgreSQL.16 --accept-package-agreements --accept-source-agreements | Tee-Object -FilePath $log -Append
# Redis for Windows (tporadowski port) or Memurai
winget search redis | Tee-Object -FilePath $log -Append
winget install -e --id Memurai.MemuraiDeveloper --accept-package-agreements --accept-source-agreements 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) {
  winget install -e --id Redis.Redis --accept-package-agreements --accept-source-agreements 2>&1 | Tee-Object -FilePath $log -Append
}
Log "DONE"
