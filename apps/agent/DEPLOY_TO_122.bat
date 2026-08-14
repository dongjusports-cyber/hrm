@echo off
chcp 65001 >nul
title DJ Agent — copy tu .123 sang .122
setlocal EnableDelayedExpansion

cd /d "%~dp0"
call :resolve_src
if errorlevel 1 exit /b 1

set "AGENT_122_IP=192.168.1.122"
set "LOCAL_IP=192.168.1.123"
set "SHARE_NAME=djhrmagent"

rem Uu tien: share dj-hrm tren .122 (ban da map T:)
set "DEST_SHARE=\\%AGENT_122_IP%\dj-hrm\apps\agent"
set "DEST_T=T:\apps\agent"
set "DEST_ADMIN=\\%AGENT_122_IP%\D$\dj-hrm\apps\agent"

echo.
echo ========================================
echo   DEPLOY Agent — .123 -^> .122
echo ========================================
echo Nguon : %SRC%
echo Dich  : %DEST_SHARE%
echo.

ping -n 1 %AGENT_122_IP% >nul 2>&1
if errorlevel 1 (
  echo LOI: Khong ping duoc %AGENT_122_IP%
  pause
  exit /b 1
)

call :enable_local_share

set "DEST="
if exist "%DEST_SHARE%\" (
  set "DEST=%DEST_SHARE%"
  echo Tim thay share: %DEST_SHARE%
) else if exist "%DEST_T%\" (
  set "DEST=%DEST_T%"
  echo Tim thay o T: %DEST_T%
) else (
  call :try_admin "%DEST_ADMIN%"
)

if not defined DEST (
  echo.
  echo Khong truy cap duoc share .122.
  echo Mo File Explorer: \\%AGENT_122_IP%\dj-hrm\apps\agent
  echo Hoac tren .122 chay PULL_FROM_123.bat
  echo   ^(\\%LOCAL_IP%\%SHARE_NAME%^)
  pause
  exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%" 2>nul

echo.
echo Dang copy toi %DEST% ...
robocopy "%SRC%" "%DEST%" /E /XD .venv __pycache__ .pytest_cache .git ^
  /XF agent_state.json *.pyc ^
  /NFL /NDL /NJH /NJS /nc /ns /np
set "RC=!ERRORLEVEL!"
if !RC! GEQ 8 (
  echo LOI robocopy ma !RC!
  pause
  exit /b 1
)

echo.
echo ========================================
echo   COPY XONG
echo ========================================
echo Tren may .122: double-click CAI_VA_CHAY_AGENT.bat
echo Duong dan: D:\dj-hrm\apps\agent  ^(hoac T:\apps\agent^)
echo.
pause
exit /b 0

:resolve_src
set "SRC=%~dp0"
if exist "%SRC%dj_agent\main.py" exit /b 0
if exist "%SRC%apps\agent\dj_agent\main.py" (
  set "SRC=%SRC%apps\agent\"
  exit /b 0
)
if exist "%SRC%..\..\apps\agent\dj_agent\main.py" (
  cd /d "%SRC%..\..\apps\agent"
  set "SRC=%CD%\"
  exit /b 0
)
echo LOI: Khong tim thay dj_agent\main.py
pause
exit /b 1

:enable_local_share
net share %SHARE_NAME% >nul 2>&1
if errorlevel 1 (
  net share %SHARE_NAME%="%SRC%" /GRANT:Everyone,READ >nul 2>&1
)
echo Share .123: \\%LOCAL_IP%\%SHARE_NAME%
exit /b 0

:try_admin
set "TRY=%~1"
echo Thu admin share: %TRY%
net use "%TRY%" /delete /y >nul 2>&1
net use "%TRY%" >nul 2>&1
if not errorlevel 1 goto :admin_ok
net use "%TRY%" /user:"%AGENT_122_IP%\ADMIN" "" >nul 2>&1
if not errorlevel 1 goto :admin_ok
exit /b 1

:admin_ok
if exist "%TRY%\" (
  set "DEST=%TRY%"
  echo    OK
)
exit /b 0
