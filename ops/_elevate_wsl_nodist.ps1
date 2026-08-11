$ErrorActionPreference = "Continue"
$log = "D:\HRM\dj-hrm\ops\wsl-install-nodist.log"
function Log($m){ "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }
Log "START wsl --install --no-distribution"
wsl --install --no-distribution 2>&1 | Tee-Object -FilePath $log -Append
Log "EXIT=$LASTEXITCODE"
wsl --status 2>&1 | Tee-Object -FilePath $log -Append
Log "DONE"
