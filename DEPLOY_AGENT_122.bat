@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0apps\agent\DEPLOY_TO_122.bat"
