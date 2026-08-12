@echo off
cd /d "%~dp0"
if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ - giai nen lai backups\dj-agent-hr122.zip
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo LOI: Chua co .venv - chay CAI_AGENT_HR122.bat truoc
  pause
  exit /b 1
)
.\.venv\Scripts\python -m dj_agent.main --mock --once
pause
