@echo off
chcp 65001 >nul
title [Thien-Admin] Mo khoa portal admin / hr.demo
cd /d "%~dp0\.."
echo.
echo === Mo khoa portal DJ-HRM (VPS) ===
echo Can file ops\vps-root.txt
echo.
python ops\unlock_portal.py
echo.
pause
