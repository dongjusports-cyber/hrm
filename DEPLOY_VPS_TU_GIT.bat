@echo off
chcp 65001 >nul
title Deploy code tu GitHub len VPS
cd /d "%~dp0"
echo.
echo Buoc 1: Dam bao da push len GitHub (git push)
git status -sb
echo.
set /p OK="Da push GitHub xong? (Y/N): "
if /i not "%OK%"=="Y" (
  echo Hay push truoc: git add ... ^&^& git commit ^&^& git push
  pause
  exit /b 1
)
echo.
echo Buoc 2: VPS git pull + deploy...
python ops\deploy_vps_from_git.py
echo.
pause
