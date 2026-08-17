$ErrorActionPreference = "Stop"
$agent = "D:\dj-hrm\apps\agent"
$py = Join-Path $agent ".venv\Scripts\pythonw.exe"
$taskName = "DJ-HRM-Agent-122"

$action = New-ScheduledTaskAction -Execute $py -Argument "-m dj_agent.main" -WorkingDirectory $agent
$logon = New-ScheduledTaskTrigger -AtLogOn
# Neu pythonw chet: 5 phut sau tu mo lai (dang chay thi bo qua).
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
Write-Host "Tu dong: luc dang nhap + moi 5 phut neu chet."
