param(
  [string]$AgentDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $AgentDir) {
  foreach ($c in @("D:\dj-hrm\apps\agent", "D:\dj-hrm\agent")) {
    if (Test-Path (Join-Path $c "dj_agent\main.py")) {
      $AgentDir = $c
      break
    }
  }
}
if (-not $AgentDir -or -not (Test-Path (Join-Path $AgentDir "dj_agent\main.py"))) {
  throw "LOI: khong thay folder agent (dj_agent\main.py)."
}

$pyExe = Join-Path $AgentDir ".venv\Scripts\python.exe"
$pyw = Join-Path $AgentDir ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyExe)) {
  throw "LOI: chua co .venv — chay 00-TAO-PYTHON-LOCAL.bat"
}
& $pyExe -c "print(1)" | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "LOI: .venv copy tu may .123. Chay 00-TAO-PYTHON-LOCAL.bat"
}
if (-not (Test-Path $pyw)) {
  $pyw = $pyExe
}

$taskName = "DJ-HRM-Agent-122"
$action = New-ScheduledTaskAction -Execute $pyw -Argument "-m dj_agent.main" -WorkingDirectory $AgentDir
$logon = New-ScheduledTaskTrigger -AtLogOn
$watch = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) `
  -RepetitionInterval (New-TimeSpan -Minutes 5) `
  -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit ([TimeSpan]::Zero) `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -Hidden

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logon, $watch) -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "XONG. Agent dang chay ngam (Task Scheduler: $taskName)."
Write-Host "Folder: $AgentDir"
Write-Host "Tu dong: luc dang nhap + moi 5 phut neu chet."
