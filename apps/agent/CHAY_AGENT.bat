@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ — copy lai goi USB-122-AGENT.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Chua co .venv — tren .122 chay 02-CAI-DAT.bat (thu muc D:\122-AGENT).
  pause
  exit /b 1
)
if not exist ".env" copy /Y ".env.hr122.example" ".env" >nul
call .venv\Scripts\python -m dj_agent.main %*
