@echo off
chcp 65001 >nul
title Dong bo sang: VPS + may .123
cd /d "%~dp0"
echo.
echo [1/2] VPS: git pull + deploy production...
python ops\deploy_vps_from_git.py
if errorlevel 1 (
  echo Deploy VPS loi — co the chua them Deploy Key: chay THEM_DEPLOY_KEY_GITHUB.bat
  pause
  exit /b 1
)
echo.
echo [2/2] May .123: git pull...
git pull origin main
if errorlevel 1 (
  echo Pull local loi
  pause
  exit /b 1
)
echo.
echo XONG — code VPS va may .123 dong bo voi GitHub.
echo DB production van chi tren VPS (khong tu dong ve .123).
echo.
pause
