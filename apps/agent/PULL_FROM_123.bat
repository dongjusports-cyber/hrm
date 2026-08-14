@echo off
chcp 65001 >nul
title DJ Agent — keo tu .123 ve .122
cd /d "%~dp0"

set "AGENT_123_IP=192.168.1.123"
set "SHARE=\\%AGENT_123_IP%\djhrmagent"
set "DEST=%~dp0"

echo Nguon : %SHARE%
echo      hoac \\%AGENT_123_IP%\dj-hrm\apps\agent ^(neu co^)
echo Dich  : %DEST%
echo.

ping -n 1 %AGENT_123_IP% >nul 2>&1
if errorlevel 1 (
  echo LOI: Khong ping duoc %AGENT_123_IP%
  pause
  exit /b 1
)

net use "%SHARE%" /delete /y >nul 2>&1
set "SRC="
if exist "%SHARE%\dj_agent\main.py" set "SRC=%SHARE%"
if not defined SRC if exist "\\%AGENT_123_IP%\dj-hrm\apps\agent\dj_agent\main.py" set "SRC=\\%AGENT_123_IP%\dj-hrm\apps\agent"

if not defined SRC (
  net use "%SHARE%" >nul 2>&1
  if exist "%SHARE%\dj_agent\main.py" set "SRC=%SHARE%"
)

if not defined SRC (
  echo LOI: Khong mo duoc nguon tu .123
  echo Tren .123 chay DEPLOY_AGENT_122.bat truoc.
  pause
  exit /b 1
)

echo Nguon thuc te: %SRC%

echo Dang copy...
robocopy "%SRC%" "%DEST%" /E /XD .venv __pycache__ .pytest_cache ^
  /XF agent_state.json *.pyc ^
  /NFL /NDL /NJH /NJS /nc /ns /np

echo.
echo PULL xong. Chay tiep: CAI_VA_CHAY_AGENT.bat
echo.
pause
