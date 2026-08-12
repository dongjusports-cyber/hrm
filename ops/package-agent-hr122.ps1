# Đóng gói DJ Sync Agent cho máy HR-Nhu (.122) — chạy trên máy .123
# Output: backups\dj-agent-hr122.zip

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$src = Join-Path $root "apps\agent"
$outDir = Join-Path $root "backups"
$zip = Join-Path $outDir "dj-agent-hr122.zip"

if (-not (Test-Path (Join-Path $src "requirements.txt"))) {
    Write-Error "Missing apps/agent/requirements.txt"
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
if (Test-Path $zip) { Remove-Item $zip -Force }

$staging = Join-Path $env:TEMP "dj-agent-hr122-pack"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

Copy-Item (Join-Path $src "requirements.txt") $staging
Copy-Item (Join-Path $src "README.md") $staging
Copy-Item (Join-Path $src "config.example.env") $staging
Copy-Item (Join-Path $src ".env.hr122.example") $staging
Copy-Item (Join-Path $src "CAI_AGENT_HR122.bat") $staging
Copy-Item (Join-Path $src "CHAY_AGENT.bat") $staging
Copy-Item (Join-Path $src "RUN_MOCK.bat") $staging
Copy-Item (Join-Path $src "RUN_ONCE.bat") $staging
Copy-Item (Join-Path $src "dj_agent") (Join-Path $staging "dj_agent") -Recurse

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zip -Force
Remove-Item $staging -Recurse -Force

Write-Host "OK: $zip"
Write-Host ""
Write-Host "Tren may .122:"
Write-Host "  1. Giai nen vao D:\dj-hrm\dj-hrm\apps\agent\"
Write-Host "  2. copy .env.hr122.example .env"
Write-Host "  3. python -m venv .venv"
Write-Host "  4. .\.venv\Scripts\pip install -r requirements.txt"
Write-Host "  5. python -m dj_agent.main --mock --once"
