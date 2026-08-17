$ErrorActionPreference = "Stop"
$agent = "D:\dj-hrm\apps\agent"
$py = Join-Path $agent ".venv\Scripts\pythonw.exe"
$taskName = "DJ-HRM-Agent-122"

$action = New-ScheduledTaskAction -Execute $py -Argument "-m dj_agent.main" -WorkingDirectory $agent
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit ([TimeSpan]::Zero) `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -Hidden

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "XONG. Agent dang chay ngam (Task Scheduler: $taskName)."
