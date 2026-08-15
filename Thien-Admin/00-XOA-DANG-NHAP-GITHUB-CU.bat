@echo off
chcp 65001 >nul
title [Thien-Admin] Xoa dang nhap GitHub cu
echo.
echo Xoa credential GitHub cu tren Windows...
cmdkey /delete:LegacyGeneric:target=git:https://github.com 2>nul
cmdkey /delete:git:https://github.com 2>nul
echo Xong. Chay lai 00-PUSH-GITHUB-MOI.bat
pause
