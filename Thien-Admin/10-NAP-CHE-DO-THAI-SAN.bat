@echo off
chcp 65001 >nul
title [Thien-Admin] Nap che do thai san / nuoi con len VPS
cd /d "%~dp0\.."
echo Nap danh sach che do tu Excel 18.08 len VPS (13 NV: 5 nuoi con, 3 mang thai, 5 nghi sau sanh).
echo.
python ops\fill_vps_wt_regimes.py
if errorlevel 1 (
    echo LOI nap che do.
    pause
    exit /b 1
)
echo.
echo XONG — F5 Portal, loc Chế độ đặc biệt, mo ho so NV kiem tra tab che do.
pause
