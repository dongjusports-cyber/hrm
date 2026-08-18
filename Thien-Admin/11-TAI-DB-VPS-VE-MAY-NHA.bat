@echo off
chcp 65001 >nul
title [Thien-Admin] Tai DB VPS ve may nha
cd /d "%~dp0\.."
echo.
echo  Chi KEOS du lieu VPS xuong may nha.
echo  KHONG ghi de DB production.
echo.
python ops\pull_vps_db_to_local.py
echo.
pause
