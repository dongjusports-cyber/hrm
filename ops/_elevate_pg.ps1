$ErrorActionPreference = "Continue"
$log = "D:\HRM\dj-hrm\ops\pg-install.log"
function Log($m){ "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }
Log "START pg"
winget install -e --id PostgreSQL.PostgreSQL.17 --accept-package-agreements --accept-source-agreements 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) {
  winget install -e --id PostgreSQL.PostgreSQL --accept-package-agreements --accept-source-agreements 2>&1 | Tee-Object -FilePath $log -Append
}
# Portable-ish: download zip binaries if winget fails
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
  Log "Trying EnterpriseDB silent via curl alternate"
  $url = "https://get.enterprisedb.com/postgresql/postgresql-16.11-1-windows-x64.exe"
  $out = "$env:TEMP\postgresql-16-installer.exe"
  try {
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
    Start-Process $out -ArgumentList "--mode unattended --superpassword djhrm_local_change_me --serverport 5432 --serviceaccountpassword djhrm_local_change_me --unattendedmodeui none" -Wait
  } catch {
    Log "EDB download failed: $_"
  }
}
Log "DONE"
Get-Service *postgres* -ErrorAction SilentlyContinue | Format-Table Name, Status | Out-String | Tee-Object -FilePath $log -Append
