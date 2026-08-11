$ErrorActionPreference = "Continue"
$log = "D:\HRM\dj-hrm\ops\wsl-install.log"
function Log($m){ "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }
Log "START elevated WSL install"
winget install -e --id Microsoft.WSL --accept-package-agreements --accept-source-agreements | Tee-Object -FilePath $log -Append
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Tee-Object -FilePath $log -Append
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Tee-Object -FilePath $log -Append
wsl --install --no-distribution 2>&1 | Tee-Object -FilePath $log -Append
Log "DONE exit=$LASTEXITCODE"
