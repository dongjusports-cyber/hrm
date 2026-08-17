@echo off
chcp 65001 >nul
title [122] 03 Chay thu 1 lan
cd /d "%~dp0"
set "AGENT=%~dp0agent"
if not exist "%AGENT%\.venv\Scripts\python.exe" (
  echo Chua cai dat — chay 02-CAI-DAT.bat truoc.
  pause
  exit /b 1
)
pushd "%AGENT%"
call ".venv\Scripts\python.exe" -m dj_agent.main --once
popd
echo.
pause
