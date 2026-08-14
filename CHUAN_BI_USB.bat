@echo off
chcp 65001 >nul
title DJ Agent — chuan bi copy USB (.123)
cd /d "%~dp0"

set "OUT=%~dp0USB-dj-agent"
set "SRC=%~dp0apps\agent"

if not exist "%SRC%\dj_agent\main.py" (
  echo LOI: Khong tim thay apps\agent
  pause
  exit /b 1
)

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%" 2>nul

echo.
echo ========================================
echo   CHUAN BI USB — Agent cho may .122
echo ========================================
echo Nguon : %SRC%
echo Dich  : %OUT%
echo.

robocopy "%SRC%" "%OUT%" /E /XD .venv __pycache__ .pytest_cache .git ^
  /XF .env agent_state.json *.pyc ^
  /NFL /NDL /NJH /NJS /nc /ns /np

copy /Y "%SRC%\.env.hr122.example" "%OUT%\.env.hr122.example" >nul 2>&1

echo.
echo XONG. Copy folder nay vao USB:
echo   %OUT%
echo.
echo Tren may .122: double-click  CAI_TU_USB.bat
echo (xem HUONG_DAN_USB.txt)
echo.
explorer "%OUT%"
pause
