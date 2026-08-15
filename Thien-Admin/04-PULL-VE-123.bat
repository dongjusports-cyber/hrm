@echo off
chcp 65001 >nul
title [Thien-Admin] Pull code ve may .123
cd /d "%~dp0\.."
call "%~dp0\..\PULL_VE_123.bat"
