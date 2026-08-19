@echo off
chcp 65001 >nul
title [Thien-Admin] Pull code ve may .123
cd /d "%~dp0\.."
echo.
echo === git pull origin main ===
git pull origin main
if errorlevel 1 (
  echo Pull loi — kiem tra mang / conflict
  pause
  exit /b 1
)
echo.
echo XONG. Code local da dong bo voi GitHub.
echo.
pause
