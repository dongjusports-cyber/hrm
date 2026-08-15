@echo off
chcp 65001 >nul
title Mo khoa admin / hr.demo tren VPS
cd /d "%~dp0"

echo.
echo === Mo khoa portal DJ-HRM (VPS) ===
echo Can file ops\vps-root.txt (IP + pass root VPS)
echo.

python ops\unlock_portal.py
echo.
pause
