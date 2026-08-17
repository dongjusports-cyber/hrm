@echo off
chcp 65001 >nul
title [122] 04 Tu chay khi mo may
cd /d "%~dp0"
set "AGENT=%~dp0agent"

net session >nul 2>&1
if errorlevel 1 (
  echo Can quyen Administrator. Dang mo lai...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

if not exist "%AGENT%\dj_agent\main.py" (
  echo LOI: thieu folder agent\
  pause
  exit /b 1
)
if not exist "%AGENT%\.venv\Scripts\python.exe" (
  echo Chua cai dat — chay 02-CAI-DAT.bat truoc.
  pause
  exit /b 1
)
"%AGENT%\.venv\Scripts\python.exe" -c "print(1)" >nul 2>&1
if errorlevel 1 (
  echo LOI: .venv hong. Chay lai 02-CAI-DAT.bat
  pause
  exit /b 1
)

echo Dang ky Agent chay ngam khi dang nhap Windows...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp004-cai-tu-chay.ps1" -AgentDir "%AGENT%"
if errorlevel 1 (
  echo LOI dang ky lich.
  pause
  exit /b 1
)
echo.
echo XONG. Khong can mo cua so nua. Log: %AGENT%\agent.log
echo.
pause
