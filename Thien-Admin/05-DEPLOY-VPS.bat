@echo off
chcp 65001 >nul
title [Thien-Admin] Deploy code len VPS
cd /d "%~dp0\.."
echo.
echo VPS git pull + deploy...
python ops\deploy_vps_from_git.py
echo.
pause
