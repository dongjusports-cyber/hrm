@echo off
chcp 65001 >nul
title DJ Sync Agent — nền 15 phút/lần (.122)
cd /d "%~dp0"

if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ — giai nen backups\dj-agent-hr122.zip vao day.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo LOI: Chua co .venv — chay CAI_AGENT_HR122.bat truoc.
  pause
  exit /b 1
)
if not exist ".env" (
  if exist ".env.hr122.example" (
    copy /Y ".env.hr122.example" ".env" >nul
    echo Da tao .env tu .env.hr122.example
  ) else (
    echo LOI: Thieu .env
    pause
    exit /b 1
  )
)

echo === DJ Sync Agent daemon ===
echo API: %DJ_API_BASE_URL%
echo Sync moi 15 phut. Ctrl+C de dung.
echo.

call .venv\Scripts\python -m dj_agent.main
