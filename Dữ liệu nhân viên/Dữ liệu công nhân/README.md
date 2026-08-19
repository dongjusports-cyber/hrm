# Snapshot JSON — một file / MSNV

Nằm trong **`Dữ liệu nhân viên/`** (cùng cấp: hồ sơ Excel + ảnh, bảng lương).

| Thư mục | Dùng khi |
|---------|----------|
| **`Dữ liệu nhân viên/Dữ liệu công nhân/`** (thư mục này) | Snapshot 1 JSON / MSNV — hồ sơ + HĐ + phụ cấp + công. Nạp lại DB test. |
| **`Dữ liệu nhân viên/Thông tin danh sách nhân viên/trich_xuat_140826/`** | Hồ sơ Excel GenusSuite 14.08 (MSNV + ảnh). Tra cứu / bổ sung thiếu. |
| **`Dữ liệu nhân viên/Salary/`** | Bảng lương Excel. |

## Snapshot (thư mục này)

- `employees/{MSNV}.json`
- `Thông tin bổ sung  14.08.26.xlsx`
- `trich_xuat_bo_sung_140826/`
- `manifest.json`
- `CHO_BO_SUNG.md`

```powershell
cd apps/api
python -m app.scripts.import_employee_snapshots "Dữ liệu nhân viên/Dữ liệu công nhân"
python -m app.scripts.import_employee_snapshots "Dữ liệu nhân viên/Dữ liệu công nhân" --with-attendance
```

## Thông tin bổ sung 14.08

```powershell
python -m app.scripts.extract_thong_tin_bo_sung
python -m app.scripts.import_thong_tin_bo_sung
```

VPS: `Thien-Admin\09-NAP-THONG-TIN-BO-SUNG.bat`

## Trích xuất hồ sơ + ảnh

`Dữ liệu nhân viên/Thông tin danh sách nhân viên/`

```powershell
python -m app.scripts.extract_empinfo_profiles
python -m app.scripts.import_employee_list_1108 "Dữ liệu nhân viên/Thông tin danh sách nhân viên" --profiles-only
```
