@echo off
chcp 65001 >nul
title Khoi phuc Docker data (docker_data.vhdx cu)
setlocal

set "ROOT=C:\DATA\Docker\DockerDesktopWSL"
set "OLD_DISK=%ROOT%\disk\docker_data.vhdx"
set "NEW_DISK=%ROOT%\DockerDesktopWSL\disk\docker_data.vhdx"
set "BAK=%ROOT%\DockerDesktopWSL\disk\docker_data.vhdx.bak_%date:~-4%%date:~3,2%%date:~0,2%"

echo.
echo ========================================
echo   KHOI PHUC DB Docker tu ban copy cu
echo ========================================
echo Ban copy cu (6GB): %OLD_DISK%
echo Docker dang dung:   %NEW_DISK%
echo.

if not exist "%OLD_DISK%" (
  echo LOI: Khong thay %OLD_DISK%
  pause
  exit /b 1
)

echo CANH BAO: Docker Desktop se TAT. Thay file vhdx.
echo           Backup ban hien tai truoc.
echo.
pause

echo [1] Tat Docker + WSL...
taskkill /IM "Docker Desktop.exe" /F >nul 2>&1
wsl --shutdown
timeout /t 5 /nobreak >nul

if exist "%NEW_DISK%" (
  echo [2] Backup ban hien tai...
  copy /Y "%NEW_DISK%" "%BAK%" >nul
  echo     -> %BAK%
)

echo [3] Copy ban cu (6GB) de thay...
copy /Y "%OLD_DISK%" "%NEW_DISK%"
if errorlevel 1 (
  echo LOI copy
  pause
  exit /b 1
)

echo.
echo XONG. Mo lai Docker Desktop, cho WSL khoi dong.
echo Kiem tra Portal — neu van 5 NV, chay NAP_NV_HIEN_PHAP.bat
echo.
pause
