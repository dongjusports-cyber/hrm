@echo off
chcp 65001 >nul
title [Thien-Admin] Keo backup VPS ve may nay
cd /d "%~dp0\.."
echo.
echo Keo file dump Postgres moi nhat tu VPS ve thu muc backups\
echo (phong truong hop VPS hong — file nay khong len Git)
echo.
python ops\pull_vps_backup.py
echo.
pause
