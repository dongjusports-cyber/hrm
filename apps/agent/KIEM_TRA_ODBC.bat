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
echo Tu dong sua .env (neu co .env):
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python fix_odbc_env.py
) else if exist "fix_odbc_env.py" (
  python fix_odbc_env.py
)
echo.
echo Sau khi cai, chay lai fix_odbc_env.py hoac CAI_AGENT_HR122.bat
pause
