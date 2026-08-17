@echo off
chcp 65001 >nul
title [Thien-Admin] Chuan USB Agent cho may .122
cd /d "%~dp0\.."
echo.
echo May .123: dong goi 1 folder USB-122-AGENT
echo (code Agent + .env VPS, KHONG kem .venv)
echo.
py -3.12 ops\pack_usb_122.py
if errorlevel 1 (
  echo LOI dong goi
  pause
  exit /b 1
)
echo.
echo Mo folder — copy CA folder USB-122-AGENT vao USB.
echo Tren .122: xoa agent cu, dan thanh D:\122-AGENT, chay 01 roi 02 roi 04.
echo.
explorer "C:\DATA\HRM\USB-122-AGENT"
pause
