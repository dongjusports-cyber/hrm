@echo off
chcp 65001 >nul
title [Thien-Admin] Nap ho so NV vao Docker local
cd /d "%~dp0\.."

echo.
echo === Nap ho so NV tu trich_xuat (Docker local, khong phai VPS) ===
echo.

docker compose ps --format "{{.Name}}" 2>nul | findstr djhrm-api >nul
if errorlevel 1 (
  echo Docker chua chay — khoi dong...
  docker compose up -d
  timeout /t 15 /nobreak >nul
)

set "TRICH=Dữ liệu nhân viên\Thông tin danh sách nhân viên\trich_xuat_140826"
if not exist "%TRICH%\employees.json" (
  echo Khong thay %TRICH% — thu trich_xuat_110826...
  set "TRICH=Dữ liệu nhân viên\Thông tin danh sách nhân viên\trich_xuat_110826"
)

if not exist "%TRICH%\employees.json" (
  echo LOI: Chua co trich_xuat. Copy tu may .123 vao Dữ liệu nhân viên\Thông tin danh sách nhân viên\
  pause
  exit /b 1
)

echo Copy du lieu vao container...
docker cp "%TRICH%" djhrm-api:/tmp/trich_xuat
for %%D in ("Dữ liệu nhân viên\Thông tin danh sách nhân viên") do docker cp "%%~fD" djhrm-api:/tmp/empinfo

echo Nap cay to chuc (bo phan/to) — giu NV hien co...
docker compose exec -T api python -m app.scripts.load_org_structure --skip-wipe

echo Gan lai bo phan/to cho NV...
docker compose exec -T api python -m app.scripts.reset_employees_from_trich_xuat --dir /tmp/trich_xuat --no-wipe

echo Gan lai punch da sync...
docker compose exec -T api python -c "from app.core.database import SessionLocal; from app.modules.integration.service import relink_punches; db=SessionLocal(); print(relink_punches(db)); db.close()"

echo Dem NV...
docker compose exec -T api python -c "from app.core.database import SessionLocal; from app.modules.mdm.models import Employee; db=SessionLocal(); print('employees', db.query(Employee).count()); db.close()"

echo.
echo XONG. F5 Portal local -^> Cham cong.
pause
