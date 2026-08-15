@echo off
chcp 65001 >nul
title [122] Kiem tra ODBC Driver 17/18
cd /d "%~dp0"
echo.
echo === Danh sach ODBC tren may .122 ===
echo.

set "PY="
if exist "D:\dj-hrm\apps\agent\.venv\Scripts\python.exe" (
  set "PY=D:\dj-hrm\apps\agent\.venv\Scripts\python.exe"
) else (
  where py >nul 2>&1 && set "PY=py -3"
  if not defined PY where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
  echo Khong tim thay Python. Mo Windows:
  echo   Win+R  --^>  odbcad32.exe  --^>  tab Drivers
  echo Doc: HUONG-DAN-ODBC.txt
  pause
  exit /b 1
)

%PY% -c "import pyodbc; d=pyodbc.drivers(); print(chr(10).join(d) if d else '(khong co driver)')"
if errorlevel 1 (
  echo.
  echo Chua cai pyodbc — chay D:\dj-hrm\apps\agent\CAI_AGENT_HR122.bat truoc
  echo Hoac mo odbcad32.exe xem tab Drivers
)

echo.
echo Can co MOT trong hai dong:
echo   ODBC Driver 17 for SQL Server
echo   ODBC Driver 18 for SQL Server
echo.
echo Doc them: HUONG-DAN-ODBC.txt
echo Buoc tiep: 02-GHEP-ENV.bat
echo.
pause
