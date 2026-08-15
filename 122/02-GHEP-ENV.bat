@echo off
chcp 65001 >nul
title [122] Ghep file .env vao agent
cd /d "%~dp0"

set "AGENT=D:\dj-hrm\apps\agent"
if not exist "%AGENT%\dj_agent\main.py" (
  echo LOI: Khong thay %AGENT%
  echo Sua duong dan AGENT trong file .bat neu may .122 dat khac D:\dj-hrm
  pause
  exit /b 1
)

echo.
echo Agent folder: %AGENT%
echo.
echo Chon cau hinh:
echo   1 = Test Docker may .123  (env-LOCAL-123.txt)
echo   2 = Production VPS        (env-VPS.txt)
echo.
set /p CH="Chon (1/2) [mac dinh 1]: "
if "%CH%"=="" set "CH=1"
if "%CH%"=="2" (
  set "SRC=%~dp0env-VPS.txt"
) else (
  set "SRC=%~dp0env-LOCAL-123.txt"
)

if not exist "%SRC%" (
  echo LOI: Thieu %SRC%
  pause
  exit /b 1
)

copy /Y "%SRC%" "%AGENT%\.env" >nul
echo.
echo Da copy vao: %AGENT%\.env
echo.

echo Tu dong chon ODBC 17/18 (neu co fix_odbc_env.py)...
if exist "%AGENT%\.venv\Scripts\python.exe" (
  "%AGENT%\.venv\Scripts\python.exe" "%AGENT%\fix_odbc_env.py"
) else if exist "%AGENT%\fix_odbc_env.py" (
  where py >nul 2>&1 && py -3 "%AGENT%\fix_odbc_env.py"
)

echo.
echo XONG. Chay tiep: 03-CHAY-AGENT-NEN.bat
pause
