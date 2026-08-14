@echo off
chcp 65001 >nul
title DJ Sync Agent — cai tu USB (.122)
setlocal EnableDelayedExpansion

set "TARGET=D:\dj-hrm\apps\agent"
cd /d "%~dp0"

rem --- Buoc 0: tu USB copy sang o D (lan dau) ---
if /i not "%~dp0"=="%TARGET%\" (
  if not defined DJ_AGENT_USB_DONE (
    echo.
    echo [USB] Copy Agent sang %TARGET% ...
    if not exist "%TARGET%" mkdir "%TARGET%"
    robocopy "%~dp0" "%TARGET%" /E /XD .venv __pycache__ .pytest_cache ^
      /XF agent_state.json .env *.pyc ^
      /NFL /NDL /NJH /NJS /nc /ns /np
    echo.
    echo Da copy xong. Tiep tuc cai dat...
    set "DJ_AGENT_USB_DONE=1"
    cd /d "%TARGET%"
    call "%TARGET%\CAI_TU_USB.bat"
    exit /b !ERRORLEVEL!
  )
)

cd /d "%TARGET%"
if not exist "dj_agent\main.py" cd /d "%~dp0"

echo.
echo ========================================
echo   DJ Sync Agent — CAI + CHAY (.122)
echo ========================================
echo Thu muc: %CD%
echo.

if not exist "dj_agent\main.py" (
  echo LOI: Thieu ma Agent trong folder nay.
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo LOI: Chua cai Python 3.12 — python.org
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
    echo LOI: Thieu .env
    pause
    exit /b 1
  )
)

echo [1/5] Xoa .venv cu...
if exist ".venv" rmdir /s /q ".venv"

echo [2/5] Tao venv...
%PY% -m venv .venv
if errorlevel 1 ( echo LOI venv & pause & exit /b 1 )

echo [3/5] Cai thu vien...
call .venv\Scripts\pip install -q -r requirements.txt
if errorlevel 1 ( echo LOI pip & pause & exit /b 1 )

echo [4/5] Sua ODBC + thu ket noi...
call .venv\Scripts\python fix_odbc_env.py
if errorlevel 1 echo CANH BAO: fix_odbc — Agent tu chon driver khi chay.

echo --- Thu mock (API .123) ---
call .venv\Scripts\python -m dj_agent.main --mock --once
if errorlevel 1 (
  echo LOI: May .123 chua chay Docker / port 8000
  pause
  exit /b 1
)

echo --- Thu doc Mitapro ---
call .venv\Scripts\python -m dj_agent.main --once

echo.
echo [5/5] Chay nen 2 phut/lan. Ctrl+C de dung.
call .venv\Scripts\python -m dj_agent.main
