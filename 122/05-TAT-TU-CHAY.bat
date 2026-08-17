@echo off
chcp 65001 >nul
title [122] 05 Tat tu chay
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp005-tat-tu-chay.ps1"
echo.
pause
