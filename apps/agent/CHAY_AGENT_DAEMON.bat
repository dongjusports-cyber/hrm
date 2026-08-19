@echo off
chcp 65001 >nul
title DJ Sync Agent — nền 2 phút/lần (.122)
cd /d "%~dp0"

if not exist "dj_agent\main.py" (
  echo LOI: Thieu folder dj_agent\ — copy lai goi USB-122-AGENT.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo LOI: Chua co .venv — tren .122 chay 02-CAI-DAT.bat (thu muc D:\122-AGENT).
  pause
  exit /b 1
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

echo === DJ Sync Agent daemon ===
echo API: %DJ_API_BASE_URL%
echo Sync moi 2 phut. Ctrl+C de dung.
echo.

call .venv\Scripts\python -m dj_agent.main

