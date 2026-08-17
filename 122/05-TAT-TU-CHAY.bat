@echo off
chcp 65001 >nul
title [122] Tat agent tu chay khi mo may

echo Dung agent + xoa lich tu-chay DJ-HRM-Agent-122 ...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp005-tat-tu-chay.ps1"

echo.
echo Neu can chay tay: 03-CHAY-AGENT-NEN.bat
echo.
pause
