@echo off
chcp 65001 >nul
title [Thien-Admin] Doi dang nhap GitHub (cu → dongjusports-cyber)
cd /d "%~dp0\.."
echo.
echo Xoa credential GitHub CU (nguyenthiendongju-hub) tren Windows...
cmdkey /delete:LegacyGeneric:target=git:https://github.com 2>nul
cmdkey /delete:git:https://github.com 2>nul
cmdkey /delete:GitHub - https://api.github.com/nguyenthiendongju-hub 2>nul
echo.
echo Da xoa (neu co). Tiep theo push se hoi dang nhap MOI.
echo.
echo Dang nhap bang:
echo   - Trinh duyet (Git Credential Manager), HOAC
echo   - Personal Access Token tu dongjusports-cyber
echo.
pause
echo.
git push -u origin main
if errorlevel 1 (
  echo.
  echo Van loi? Lam tay:
  echo   1. Windows: Tim kiem "Credential Manager" / Quan ly thong tin dang nhap
  echo   2. Xoa muc lien quan github.com
  echo   3. Chay lai file nay
  pause
  exit /b 1
)
echo.
echo XONG — code da tren https://github.com/dongjusports-cyber/hrm
echo Tiep: 01-THEM-DEPLOY-KEY.bat
pause
