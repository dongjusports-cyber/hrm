@echo off
chcp 65001 >nul
title [122] 01 Kiem tra ODBC
cd /d "%~dp0"
echo.
echo May .122 — can ODBC Driver 17 hoac 18 for SQL Server
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if defined PY (
  %PY% -c "import pyodbc; d=pyodbc.drivers(); print('\n'.join(x for x in d if 'SQL Server' in x) or '(chua co driver SQL)')" 2>nul
  if errorlevel 1 (
    echo Chua cai pyodbc — khong sao. Buoc 02 se cai.
    echo Ban van mo duoc: Win+R  -^>  odbcad32.exe  -^>  tab Drivers
  )
) else (
  echo Chua thay Python. Buoc 02 can Python 3.12 ^(python.org, tick Add to PATH^).
  echo Tam thoi: Win+R  -^>  odbcad32.exe  -^>  tab Drivers
)

echo.
echo Can thay MOT dong:
echo   ODBC Driver 17 for SQL Server
echo   ODBC Driver 18 for SQL Server
echo.
echo Tiep theo:  02-CAI-DAT.bat
echo.
pause
