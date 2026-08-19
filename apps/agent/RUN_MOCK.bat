@echo off
cd /d "%~dp0"
if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ - copy lai goi USB-122-AGENT
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo LOI: Chua co .venv - tren .122 chay 02-CAI-DAT.bat (D:\122-AGENT)
  pause
  exit /b 1
)
.\.venv\Scripts\python -m dj_agent.main --mock --once
pause
