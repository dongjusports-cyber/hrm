# DJ HRM — chạy local không Docker (Postgres + Memurai/Redis + uvicorn + Vite)
# Yêu cầu: PostgreSQL 16 service, Memurai/Redis :6379, Node.js, apps/api/.venv

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$env:Path = "C:\Program Files\PostgreSQL\16\bin;C:\Program Files\nodejs;" + $env:Path
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Get-Content (Join-Path $Root ".env") | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $k, $v = $_.Split('=', 2)
  if ($k -and $null -ne $v) { Set-Item -Path "Env:$k" -Value $v }
}

# Đảm bảo URL localhost (native)
$env:DATABASE_URL = "postgresql+psycopg://djhrm:djhrm_local_change_me@127.0.0.1:5432/djhrm"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"

Start-Process -FilePath (Join-Path $Root "apps\api\.venv\Scripts\uvicorn.exe") `
  -ArgumentList @("app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload") `
  -WorkingDirectory (Join-Path $Root "apps\api")

Start-Process -FilePath "npm" `
  -ArgumentList @("run", "dev", "--", "--host", "0.0.0.0", "--port", "5173") `
  -WorkingDirectory (Join-Path $Root "apps\web")

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173/login"
Write-Host "DJ HRM local: http://localhost:5173  API: http://localhost:8000/docs"
