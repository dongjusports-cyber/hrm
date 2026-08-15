@echo off
chcp 65001 >nul
title [Thien-Admin] Mo GitHub Deploy keys (repo moi)
echo Repo: dongjusports-cyber/hrm
start https://github.com/login
timeout /t 2 /nobreak >nul
start https://github.com/dongjusports-cyber/hrm/settings/keys
pause
