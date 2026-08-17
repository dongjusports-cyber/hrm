param(
  [Parameter(Mandatory = $true)]
  [string]$AgentDir
)

$ErrorActionPreference = "Stop"
$AgentDir = $AgentDir.TrimEnd("\")
$pyw = Join-Path $AgentDir ".venv\Scripts\pythonw.exe"
$pyExe = Join-Path $AgentDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pyExe)) {
  throw "LOI: chua chay 02-CAI-DAT.bat"
}
& $pyExe -c "print(1)" | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "LOI: .venv hong. Chay lai 02-CAI-DAT.bat"
}
if (-not (Test-Path $pyw)) { $pyw = $pyExe }

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
Write-Host "XONG. Task: $taskName"
Write-Host "Folder: $AgentDir"
