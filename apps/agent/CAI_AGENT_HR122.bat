@echo off
chcp 65001 >nul
title DJ Sync Agent - cai tren HR-Nhu (.122)
echo.
echo === DJ Sync Agent - tu cai tren may nay ===
echo.

cd /d "%~dp0"
if not exist "requirements.txt" (
  echo LOI: Thieu requirements.txt - giai nen dj-agent-hr122.zip vao folder nay truoc.
  pause
  exit /b 1
)
if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ - copy tu may .123 hoac giai nen lai dj-agent-hr122.zip
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo LOI: Chua cai Python. Tai python.org 3.12 roi chay lai.
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.hr122.example" (
    copy /Y ".env.hr122.example" ".env"
    echo Da tao .env tu .env.hr122.example
  ) else (
    echo LOI: Thieu .env va .env.hr122.example
    pause
    exit /b 1
  )
)

echo Tao virtualenv...
python -m venv .venv
call .venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
  echo LOI: pip install that bai
  pause
  exit /b 1
)

echo.
echo === Thu mock (khong can SQL) ===
call .venv\Scripts\python -m dj_agent.main --mock --once
if errorlevel 1 (
  echo LOI mock - kiem tra .env DJ_API_BASE_URL=http://192.168.1.123:8000
  echo va firewall port 8000 tren may .123
  pause
  exit /b 1
)

echo.
echo === Thu doc Mitapro that ===
call .venv\Scripts\python -m dj_agent.main --once

echo.
echo XONG. De chay nen 15 phut/lan:
echo   .venv\Scripts\python -m dj_agent.main
echo.
pause
