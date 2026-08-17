@echo off
chcp 65001 >nul
title [122] 02 Cai dat Agent (Python local)
cd /d "%~dp0"
set "AGENT=%~dp0agent"

if not exist "%AGENT%\dj_agent\main.py" (
  echo LOI: Thieu folder agent\ — copy lai USB-122-AGENT cho du.
  pause
  exit /b 1
)
if not exist "%AGENT%\.env" (
  echo LOI: Thieu agent\.env — chay 08-CHUAN-USB-122.bat tren may .123 roi copy lai.
  pause
  exit /b 1
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo LOI: May .122 chua cai Python 3.12
  echo Tai python.org — cai 3.12 — TICK "Add python.exe to PATH" — roi chay lai file nay.
  pause
  exit /b 1
)

echo.
echo Cai Python local trong folder nay ^(khong dung Python may .123^).
echo File .env GIU NGUYEN.
echo.

if exist "%AGENT%\.venv\Scripts\python.exe" (
  "%AGENT%\.venv\Scripts\python.exe" -c "print(1)" >nul 2>&1
  if errorlevel 1 (
    echo .venv hong — xoa, tao lai.
    rmdir /s /q "%AGENT%\.venv"
  )
)

if not exist "%AGENT%\.venv\Scripts\python.exe" (
  echo Tao .venv ...
  %PY% -m venv "%AGENT%\.venv"
  if errorlevel 1 (
    echo LOI: khong tao duoc .venv
    pause
    exit /b 1
  )
)

echo Cai thu vien ...
call "%AGENT%\.venv\Scripts\pip.exe" install -r "%AGENT%\requirements.txt"
if errorlevel 1 (
  echo LOI: pip that bai
  pause
  exit /b 1
)

echo Chon ODBC 17/18 ...
pushd "%AGENT%"
call ".venv\Scripts\python.exe" fix_odbc_env.py
echo.
echo Thu day 1 lan len VPS ...
call ".venv\Scripts\python.exe" -m dj_agent.main --once
set "RC=%ERRORLEVEL%"
popd

echo.
if "%RC%"=="0" (
  echo XONG. Tiep theo: 04-CAI-TU-CHAY.bat  ^(chuot phai / Run as administrator^)
) else (
  echo Thu 1 lan chua xong — xem ODBC / Mitapro SQL.
  echo Van co the chay 04; hoac sua ODBC roi chay lai 02.
)
echo.
pause
exit /b %RC%
