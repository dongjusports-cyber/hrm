@echo off
chcp 65001 >nul
title [122] Chay Agent nen (2 phut/lan)
cd /d "%~dp0"
call "%~dp0_tim-agent.cmd"
if not defined AGENT (
  pause
  exit /b 1
)
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
  echo Chua cai .venv — chay 00-TAO-PYTHON-LOCAL.bat
  pause
  exit /b 1
)
.venv\Scripts\python.exe -c "print(1)" >nul 2>&1
if errorlevel 1 (
  echo LOI: .venv copy tu may .123 ^(Dongju Spots Pro^).
  echo Chay 00-TAO-PYTHON-LOCAL.bat  ^(giu file .env^)
  pause
  exit /b 1
)

echo === Agent nen — Ctrl+C de dung ===
echo API trong .env — sync moi 2 phut
echo.
call "%AGENT%\CHAY_AGENT_DAEMON.bat"
