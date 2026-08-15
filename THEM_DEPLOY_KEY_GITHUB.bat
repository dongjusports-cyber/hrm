@echo off
chcp 65001 >nul
title Them Deploy Key len GitHub (mot lan)
cd /d "%~dp0"
echo.
echo === Buoc 1: Tao / lay public key tren VPS ===
if not exist ops\github_deploy_key.pub (
  python ops\setup_github_deploy_key.py
  if errorlevel 1 pause & exit /b 1
)
echo.
echo === Buoc 2: Copy key + mo trang GitHub ===
if not exist "Thien-Admin" mkdir "Thien-Admin"
copy /Y ops\github_deploy_key.pub "Thien-Admin\DEPLOY-KEY.txt" >nul
powershell -NoProfile -Command "Get-Content -Raw 'ops\github_deploy_key.pub' | Set-Clipboard"
echo Da copy public key vao clipboard.
echo (Ban sao: Thien-Admin\DEPLOY-KEY.txt)
echo.
echo Trong trang GitHub vua mo:
echo   1. Dang nhap tai khoan dongjusports-cyber neu chua login
echo   2. Settings ^> Deploy keys ^> Add deploy key
echo   Title: dj-hrm-vps-deploy
echo   Key:   Ctrl+V
echo   KHONG tick "Allow write access"
echo.
echo Mo trang repo (neu 404: doc Thien-Admin\HUONG-DAN-DEPLOY-KEY.txt)
start https://github.com/login
timeout /t 2 /nobreak >nul
start https://github.com/dongjusports-cyber/hrm/settings/keys
pause
echo.
echo === Buoc 3: Kiem tra VPS ket noi GitHub ===
python ops\verify_github_deploy_key.py
echo.
pause
