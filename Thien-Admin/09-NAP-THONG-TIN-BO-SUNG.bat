@echo off
chcp 65001 >nul
title [Thien-Admin] Nap thong tin bo sung len VPS
cd /d "%~dp0\.."
echo Nap hon nhan / so con / SDT / STK trong tu file Excel 14.08 len VPS.
echo Can da deploy code moi (05-DEPLOY-VPS.bat) truoc.
echo.
python ops\fill_vps_thong_tin_bo_sung.py
if errorlevel 1 (
  echo LOI nap du lieu.
  pause
  exit /b 1
)
echo.
echo XONG — F5 Portal, mo ho so NV kiem tra hon nhan / so con.
pause
