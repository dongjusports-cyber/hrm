@echo off
chcp 65001 >nul
title [Thien-Admin] Nap anh chan dung NV len VPS
cd /d "%~dp0\.."
echo Nap anh photos/{MSNV}.jpg len VPS — gan dung ma nhan vien.
echo Khong xoa NV, khong sua luong / ngay sinh.
echo.
python ops\fill_vps_employee_photos.py
if errorlevel 1 (
    echo LOI nap anh.
    pause
    exit /b 1
)
echo.
echo XONG — F5 Portal, mo ho so NV kiem tra anh.
pause
