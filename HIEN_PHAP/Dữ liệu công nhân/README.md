# Dữ liệu công nhân — một chỗ (đã lọc trùng 2026-08-17)

Hai loại dữ liệu, **không copy chồng**:

| Thư mục | Dùng khi |
|---------|----------|
| **`HIEN_PHAP/Dữ liệu công nhân/`** (thư mục này) | Snapshot 1 JSON / MSNV — hồ sơ + HĐ + phụ cấp + công. Nạp lại DB test. |
| **`HIEN_PHAP/Thông tin danh sách nhân viên/trich_xuat_140826/`** | Hồ sơ Excel GenusSuite 14.08 (361 MSNV + ảnh). Tra cứu / bổ sung thiếu. |

## Snapshot (thư mục này)

- `employees/{MSNV}.json` — **454** file (export 2026-08-15 + bổ sung hôn nhân/SĐT 14.08).
- `Thông tin bổ sung  14.08.26.xlsx` — nguồn HR 14.08 (hôn nhân, số con, STK, SĐT).
- `trich_xuat_bo_sung_140826/` — JSON/CSV đã parse từ file trên.
- `manifest.json`
- `CHO_BO_SUNG.md` — việc HR còn điền trên web.

```powershell
cd apps/api
python -m app.scripts.import_employee_snapshots "HIEN_PHAP/Dữ liệu công nhân"
python -m app.scripts.import_employee_snapshots "HIEN_PHAP/Dữ liệu công nhân" --with-attendance
```

## Thông tin bổ sung 14.08 (hôn nhân, số con, SĐT)

File: `Thông tin bổ sung  14.08.26.xlsx`

```powershell
python -m app.scripts.extract_thong_tin_bo_sung
python -m app.scripts.import_thong_tin_bo_sung
```

VPS (sau deploy code): `Thien-Admin\09-NAP-THONG-TIN-BO-SUNG.bat`

## Trích xuất hồ sơ + ảnh

`HIEN_PHAP/Thông tin danh sách nhân viên/`

- Nguồn chuẩn: `Thông tin full DS công nhân 14.08.xls`
- Output: `trich_xuat_140826/` (361 MSNV — gồm 8722 Lê Phát Tài, 8820 Huỳnh Gia Kỳ gom từ bản 11.08; **315 ảnh**)
- Excel 11.08 giữ làm nguồn cũ; thư mục `trich_xuat_110826` (0 ảnh) đã xóa.

```powershell
python -m app.scripts.extract_empinfo_profiles
python -m app.scripts.import_employee_list_1108 "HIEN_PHAP/Thông tin danh sách nhân viên" --profiles-only
```
