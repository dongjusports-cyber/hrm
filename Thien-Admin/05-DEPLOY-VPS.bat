@echo off
chcp 65001 >nul
title [Thien-Admin] Deploy code len VPS
cd /d "%~dp0\.."
call "%~dp0\..\DEPLOY_VPS_TU_GIT.bat"
