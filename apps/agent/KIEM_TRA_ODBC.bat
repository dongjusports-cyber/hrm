@echo off
chcp 65001 >nul
echo === ODBC drivers tren may nay ===
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python -c "import pyodbc; d=pyodbc.drivers(); print('\n'.join(d) if d else '(khong co driver)')"
) else (
  python -c "import pyodbc; d=pyodbc.drivers(); print('\n'.join(d) if d else '(khong co driver)')"
)
echo.
echo Can thay: ODBC Driver 17 for SQL Server  HOAC  ODBC Driver 18 for SQL Server
echo Tai: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
echo.
echo Sau khi cai, sua .env dong MITAPRO_ODBC cho dung ten Driver trong list tren.
pause
