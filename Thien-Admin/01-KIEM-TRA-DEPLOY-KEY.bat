@echo off
chcp 65001 >nul
title [Thien-Admin] Kiem tra Deploy Key
cd /d "%~dp0\.."
echo.
python ops\verify_github_deploy_key.py
echo.
pause
