@echo off
chcp 65001 >nul
title [122] Tao Python local — xoa .venv copy tu may khac
cd /d "%~dp0"
call "%~dp0_tim-agent.cmd"
if not defined AGENT (
  pause
  exit /b 1
)

echo.
echo Agent: %AGENT%
echo.
echo Loi "No Python at ... Dongju Spots Pro" = folder .venv copy tu may .123.
echo File nay XOA .venv roi tao Python MOI tren may .122.
echo File .env GIU NGUYEN (khong dung).
echo.
pause

if exist "%AGENT%\.venv" (
  echo Dang xoa %AGENT%\.venv ...
  rmdir /s /q "%AGENT%\.venv"
)

if exist "%AGENT%\CAI_AGENT_HR122.bat" (
  call "%AGENT%\CAI_AGENT_HR122.bat"
) else (
  echo LOI: Thieu %AGENT%\CAI_AGENT_HR122.bat
  echo Copy them apps\agent tu may .123 (khong kem .venv).
  pause
  exit /b 1
)
