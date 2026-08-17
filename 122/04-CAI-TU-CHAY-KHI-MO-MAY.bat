@echo off
chcp 65001 >nul
title [122] Cai agent tu chay khi mo may
cd /d "%~dp0"
call "%~dp0_tim-agent.cmd"
if not defined AGENT (
  pause
  exit /b 1
)

net session >nul 2>&1
if errorlevel 1 (
  echo Can quyen Administrator de dang ky Task Scheduler.
  echo Dang mo lai voi quyen Admin...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

if not exist "%AGENT%\.env" (
  echo Chua co .env — chay 02-GHEP-ENV.bat truoc
  pause
  exit /b 1
)
if not exist "%AGENT%\.venv\Scripts\python.exe" (
  echo Chua co Python local. Chay 00-TAO-PYTHON-LOCAL.bat truoc.
  pause
  exit /b 1
)
"%AGENT%\.venv\Scripts\python.exe" -c "print(1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo LOI: .venv copy tu may .123 ^(Dongju Spots Pro^) — khong chay duoc tren may nay.
  echo Chay:  00-TAO-PYTHON-LOCAL.bat
  echo ^(xoa .venv, tao Python moi; giu file .env^)
  echo.
  pause
  exit /b 1
)

echo Dang dang ky Task Scheduler: DJ-HRM-Agent-122
echo  Agent: %AGENT%
echo  - Khi Windows dang nhap user → agent chay ngam ^(khong cua so^)
echo  - Tat may / dang xuat → agent dung
echo  - Neu agent chet: Task Scheduler mo lai moi 5 phut
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp004-cai-tu-chay.ps1" -AgentDir "%AGENT%"
if errorlevel 1 (
  echo.
  echo LOI: khong dang ky duoc lich. Chay lai file nay ^(chuot phai / Run as administrator^)
  echo hoac dung 03-CHAY-AGENT-NEN.bat
  pause
  exit /b 1
)

echo.
echo Khong can mo 03-CHAY-AGENT-NEN.bat moi sang nua.
echo Log: %AGENT%\agent.log
echo Muon tat tu-chay: 05-TAT-TU-CHAY.bat
echo.
pause
