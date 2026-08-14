@echo off
chcp 65001 >nul
title Chuan bi VPS — backup local + huong dan setup
cd /d "%~dp0"

echo.
echo === 1. Kiem tra Docker local ===
docker compose ps --format "{{.Name}}" 2>nul | findstr djhrm-api >nul
if errorlevel 1 (
  echo Docker chua chay — khoi dong...
  docker compose up -d
  timeout /t 12 /nobreak >nul
)

echo.
echo === 2. Backup DB local (359 NV) de dua len VPS ===
if not exist backups mkdir backups
docker exec djhrm-postgres pg_dump -U djhrm -d djhrm -Fc -f /tmp/djhrm_local.dump
docker cp djhrm-postgres:/tmp/djhrm_local.dump backups\djhrm_local_latest.dump
for %%F in (backups\djhrm_local_latest.dump) do echo    %%~zF bytes — %%~fF

echo.
echo === 3. Dem NV tren may local ===
docker compose exec -T api python -c "from app.core.database import SessionLocal; from app.modules.mdm.models import Employee, Department, Team; db=SessionLocal(); print('  employees', db.query(Employee).count()); print('  depts', db.query(Department).count()); print('  teams', db.query(Team).count()); db.close()"

echo.
echo === 4. Huong dan setup VPS (may nha hoac day) ===
echo.
echo   a) Mua VPS xong — tao file ops\vps-root.txt tu ops\vps-root.txt.example
echo      Dong 1: IP VPS
echo      Dong 2: mat khau root
echo.
echo   b) DNS dongju-v.com: A record  hrm  -^>  IP VPS
echo.
echo   c) Chay 1 lenh (PowerShell):
echo      powershell -ExecutionPolicy Bypass -File ops\SETUP_VPS.ps1
echo.
echo   Script tu dong: SSH, Docker, deploy, restore 359 NV tu backup.
echo.
pause
