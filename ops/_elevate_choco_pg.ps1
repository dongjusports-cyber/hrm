$ErrorActionPreference = "Continue"
$log = "D:\HRM\dj-hrm\ops\pg-install2.log"
function Log($m){ "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }
Log "START"
# Install Chocolatey if missing
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
  Log "Installing Chocolatey"
  Set-ExecutionPolicy Bypass -Scope Process -Force
  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
  Invoke-Expression ((New-Object System.Net.WebClient).DownloadString("https://community.chocolatey.org/install.ps1"))
}
$env:Path = "C:\ProgramData\chocolatey\bin;" + $env:Path
Log "choco install postgresql16"
choco install postgresql16 -y --params '/Password:djhrm_local_change_me' 2>&1 | Tee-Object -FilePath $log -Append
Log "DONE last=$LASTEXITCODE"
Get-Service *postgres* -ErrorAction SilentlyContinue | Format-Table Name, Status | Out-String | Tee-Object -FilePath $log -Append
