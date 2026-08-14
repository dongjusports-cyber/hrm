@echo off
chcp 65001 >nul
title DJ Sync Agent — tu dong cai + chay (.122)
cd /d "%~dp0"

echo.
echo ========================================
echo   DJ Sync Agent — CAI + CHAY (.122)
echo ========================================
echo.

if not exist "dj_agent\main.py" (
  echo Chua co ma Agent — thu keo tu .123...
  if exist "PULL_FROM_123.bat" (
    call "PULL_FROM_123.bat"
  )
)

if not exist "dj_agent\main.py" (
  echo LOI: Van thieu ma Agent.
  echo   Cach 1: Tren .123 chay DEPLOY_AGENT_122.bat
  echo   Cach 2: Tren .122 chay PULL_FROM_123.bat
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo LOI: Chua cai Python 3.12 — tai python.org roi chay lai.
    pause
    exit /b 1
  )
  set "PY=py -3"
) else (
  set "PY=python"
)

if not exist ".env" (
  if exist ".env.hr122.example" (
    copy /Y ".env.hr122.example" ".env" >nul
    echo Da tao .env tu .env.hr122.example
  ) else (
    echo LOI: Thieu file .env
    pause
    exit /b 1
  )
)

echo [1/5] Xoa .venv cu (neu copy tu may khac)...
if exist ".venv" rmdir /s /q ".venv"

echo [2/5] Tao virtualenv moi tren may nay...
%PY% -m venv .venv
if errorlevel 1 (
  echo LOI: khong tao duoc .venv
  pause
  exit /b 1
)

echo [3/5] Cai thu vien...
call .venv\Scripts\pip install -q -r requirements.txt
if errorlevel 1 (
  echo LOI: pip install that bai
  pause
  exit /b 1
)

echo [4/5] Sua ODBC + thu ket noi...
call .venv\Scripts\python fix_odbc_env.py
if errorlevel 1 echo CANH BAO: fix_odbc_env loi — Agent van tu chon driver khi chay.
echo.
echo --- Thu mock (Agent -^> API .123, khong can SQL) ---
call .venv\Scripts\python -m dj_agent.main --mock --once
if errorlevel 1 (
  echo.
  echo LOI mock: kiem tra may .123 dang chay Docker va port 8000.
  echo Trong .env: DJ_API_BASE_URL=http://192.168.1.123:8000
  pause
  exit /b 1
)

echo.
echo --- Thu doc Mitapro SQL ---
call .venv\Scripts\python -m dj_agent.main --once
if errorlevel 1 (
  echo.
  echo CANH BAO: Doc SQL loi — xem KIEM_TRA_ODBC.bat neu can.
  echo Van co the chay nen; lan sau co the thanh cong sau khi sua ODBC.
)

echo.
echo [5/5] Chay Agent nen (2 phut/lan). Ctrl+C de dung.
echo.
call .venv\Scripts\python -m dj_agent.main
