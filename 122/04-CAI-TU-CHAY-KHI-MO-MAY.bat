@echo off
chcp 65001 >nul
title [122] Cai agent tu chay khi mo may
set "AGENT=D:\dj-hrm\apps\agent"

if not exist "%AGENT%\dj_agent\main.py" (
  echo LOI: Khong thay %AGENT%
  pause
  exit /b 1
)
if not exist "%AGENT%\.env" (
  echo Chua co .env — chay 02-GHEP-ENV.bat truoc
  pause
  exit /b 1
)
if not exist "%AGENT%\.venv\Scripts\pythonw.exe" (
  echo Chua cai .venv — chay: %AGENT%\CAI_AGENT_HR122.bat
  pause
  exit /b 1
)

echo Dang dang ky Task Scheduler: DJ-HRM-Agent-122
echo  - Khi Windows dang nhap user → agent chay ngam ^(khong cua so^)
echo  - Tat may / dang xuat → agent dung
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp004-cai-tu-chay.ps1"
if errorlevel 1 (
  echo.
  echo LOI: khong dang ky duoc lich. Thu chay lai file nay, hoac van dung 03-CHAY-AGENT-NEN.bat
  pause
  exit /b 1
)

echo.
echo Khong can mo 03-CHAY-AGENT-NEN.bat moi sang nua.
echo Log: %AGENT%\agent.log
echo Muon tat tu-chay: 05-TAT-TU-CHAY.bat
echo.
pause
