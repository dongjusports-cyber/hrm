@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ — giai nen backups\dj-agent-hr122.zip vao day.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Chua co .venv — chay CAI_AGENT_HR122.bat truoc.
  pause
  exit /b 1
)
if not exist ".env" copy /Y ".env.hr122.example" ".env" >nul
call .venv\Scripts\python -m dj_agent.main %*
