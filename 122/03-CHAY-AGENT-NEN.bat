@echo off
chcp 65001 >nul
title [122] Chay Agent nen (2 phut/lan)
set "AGENT=D:\dj-hrm\apps\agent"
cd /d "%AGENT%"

if not exist "dj_agent\main.py" (
  echo LOI: Thieu %AGENT%\dj_agent\
  pause
  exit /b 1
)
if not exist ".env" (
  echo Chua co .env — chay 02-GHEP-ENV.bat truoc
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Chua cai .venv — chay: %AGENT%\CAI_AGENT_HR122.bat
  pause
  exit /b 1
)

echo === Agent nen — Ctrl+C de dung ===
echo API trong .env — sync moi 2 phut
echo.
call "%AGENT%\CHAY_AGENT_DAEMON.bat"
