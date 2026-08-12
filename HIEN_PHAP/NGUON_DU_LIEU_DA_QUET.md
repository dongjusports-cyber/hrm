# Mục lục nguồn dữ liệu nhân viên (đã quét)

> Ngày quét: **2026-08-11** · Máy nhà · Agent Cursor  
> Mục đích: **không cần quét lại** khi bổ sung hồ sơ DJ-HRM — mở file này trước.

Hai thư mục liên quan (file này được copy vào **cả hai**):

| Thư mục | Vai trò |
|---------|---------|
| `HIEN_PHAP/Thông tin danh sách nhân viên/` | **Nguồn PII chính** (Excel hồ sơ + tổ) |
| `HIEN_PHAP/GenuSuite HRM/` | Schema / mã nghiệp vụ GenusSuite — **hầu như không có hồ sơ NV từng người** |
| `HIEN_PHAP/Salary/` (tham chiếu) | Bảng lương 2026 — số TK, CCCD, kênh ATM/CASH |

Script DJ-HRM đã dùng:

- `apps/api/app/scripts/import_employee_list_1108.py` — nạp 3 file Excel (`--profiles-only` an toàn)
- `apps/api/app/scripts/empinfo_lookup_map.py` — map nơi sinh / nơi cấp / học vấn / loại HĐ
- `apps/api/app/scripts/fill_bank_from_salary.py` — chỉ bổ sung STK trống từ lương
- `apps/api/app/scripts/reseed_lookup_names.py` — sửa tên danh mục lookup

**CẤM** trên DB công ty đã có dữ liệu thật: `load_org_structure`, `import_genussuite_2026` (full wipe/import).

---

## 1. `Thông tin danh sách nhân viên/` — 3 file Excel

### 1.1 `Bộ phận_11.08.xlsx` (~11 KB)

| Hạng mục | Chi tiết |
|----------|----------|
| Sheet | 1 sheet, cột A |
| Dòng 0 | Header: `Position Bộ Phận` |
| Nội dung | **30 tên tổ** còn hiệu lực (tháng 7/2026) |
| Dùng để | Danh sách tổ hợp lệ khi sync org / nghiệm thu cây tổ |

Mẫu tổ: Design, Purchase, Ex-Import, Sales, Accounting, Cleaner, …

### 1.2 `Danh sách Nhân Viên - Bộ phận hiện tại.xls` (~116 KB)

| Hạng mục | Chi tiết |
|----------|----------|
| Tiêu đề | `BASIC SALARY SUMMARY REPORT` |
| Header (dòng 2) | NO, DEPARTMENT, GROUP, EMP ID, FULL NAME, JOIN DATE, POSITION, PRO SALARY, BASIC SALARY, PCCC+HSE_AMT, POS_AMT, TOXIC_AMT, INDUS_AMT, TRANS_AMT, TECH_AMT, OTHER_AMT, TOTAL, UNION |
| Dữ liệu | Từ dòng 3 · **~354 NV** · 18 cột |
| Encoding tên | UTF-8 tiếng Việt **đúng** trong file |

| Cột | Index | Map DJ-HRM |
|-----|-------|------------|
| DEPARTMENT | 1 | Bộ phận (tên) |
| GROUP | 2 | Tổ (tên) |
| EMP ID | 3 | `employees.employee_code` |
| FULL NAME | 4 | `full_name` (dự phòng nếu thiếu file 1.3) |
| JOIN DATE | 5 | `join_date` |
| POSITION | 6 | `position_title` |
| PRO SALARY | 7 | `probation_salary` (script hiện ưu tiên file 1.3) |
| BASIC SALARY | 8 | `contract_salary` |
| POS/TOXIC/…_AMT | 9–15 | Phụ cấp — **chưa** nạp hàng loạt vào bảng phụ cấp (có thể làm sau) |
| UNION | 17 | Công đoàn Y/N — chưa map cột riêng |

### 1.3 `Thông tin danh sách công nhân 11.08.26.xls` (~203 KB) — **PII đầy đủ nhất**

| Hạng mục | Chi tiết |
|----------|----------|
| Tiêu đề | `THE LIST OF EMPLOYEES` |
| Header (dòng 2) | Dept, EmpID, Full Name, Picture, Birthday, Join Date, Place Of Birth, Basic Salary, Group, Sex, Position, Tel, Education, Addr, PersonID, Place_per_ID, Issue_DT, Social No, Contract No, Start Contract, End Contract, Left Date |
| Dữ liệu | Từ dòng 3 · **~359 NV** · 22 cột |
| Encoding tên | UTF-8 tiếng Việt **đúng** |

| Cột Excel | Index | → Cột / ý DJ-HRM |
|-----------|-------|------------------|
| Dept | 0 | Bộ phận (tên) |
| EmpID | 1 | `employee_code` |
| Full Name | 2 | `full_name` (**ưu tiên ghi đè** — sửa mojibake) |
| Picture | 3 | Ảnh — thường trống trong file này |
| Birthday | 4 | `birth_date` |
| Join Date | 5 | `join_date` |
| Place Of Birth | 6 | text → `birth_place_code` (lookup 34 tỉnh/TP) |
| Basic Salary | 7 | `contract_salary` + `labour_contracts.base_salary` |
| Group | 8 | Tổ |
| Sex | 9 | `gender` (M/F) |
| Position | 10 | `position_title` |
| Tel | 11 | `phone` |
| Education | 12 | → `education_code` dạng `EDUCATION_LEVEL00x` |
| Addr | 13 | `permanent_address` |
| PersonID | 14 | `id_number` (CCCD/CMND) |
| Place_per_ID | 15 | text → `id_issue_place_code` |
| Issue_DT | 16 | `id_issue_date` |
| Social No | 17 | `si_book_no` |
| Contract No | 18 | suy `contract_type_code` (vd. `1514/VTH` → VTH) |
| Start Contract | 19 | `contract_signed_at` + HĐ `start_date`/`sign_date` |
| End Contract | 20 | HĐ `end_date` (VTH thường trống) |
| Left Date | 21 | `resign_date` + `status=resigned` |

**Không có trong file này (đừng bịa):** dân tộc, tôn giáo, hôn nhân, địa chỉ tạm trú, liên hệ khẩn, người phụ thuộc.

### Kết quả nạp máy nhà (2026-08-11, `--profiles-only`)

| Trường | Số đã có (trên 453 NV) |
|--------|-------------------------|
| Nơi sinh (`birth_place_code`) | ~348 |
| Nơi cấp giấy tờ | ~346 |
| Quốc tịch (mặc định VN) | ~359 |
| Học vấn `EDUCATION_LEVEL*` | ~330 |
| Địa chỉ thường trú | ~359 |
| SĐT | ~323 |
| Số sổ BHXH | ~236 |
| STK ngân hàng | ~415 (chủ yếu từ lương, không phải file này) |
| Tên còn mojibake | ~74 (NV **không** có trong 359 dòng Excel) |

Lệnh tham chiếu:

```powershell
docker cp "D:/dj-hrm/dj-hrm/HIEN_PHAP/Thông tin danh sách nhân viên" djhrm-api:/tmp/empinfo
docker compose exec api python -m app.scripts.import_employee_list_1108 /tmp/empinfo --profiles-only --dry-run
docker compose exec api python -m app.scripts.import_employee_list_1108 /tmp/empinfo --profiles-only
```

---

## 2. `GenuSuite HRM/` — file và ích gì cho DJ-HRM

| File | Size (gần đúng) | Nội dung đã quét | Dùng để nạp hồ sơ NV? |
|------|-----------------|------------------|------------------------|
| `Master_Data.sql` | ~12 MB | Chủ yếu `INSERT THR_ABWORKGRP` (tổ), `THR_HOLIDAY_MANAGE` | **Không** — không có dump `THR_ABEMP` / hồ sơ từng người |
| `Org_Structure_Data..sql` | ~87 KB | Dữ liệu cây tổ chức | Đã dùng gián tiếp qua script org (cẩn thận trên DB công ty) |
| `Org_Structure_DDL.sql` | ~23 KB | DDL tổ chức | Tham chiếu schema |
| `Common_Codes.csv` | ~139 KB | Danh mục GenusSuite (HRAB*, quốc tịch VIE/KOR, loại HĐ VTH/HD1/TV, nhóm…) | Tham chiếu mã — **không** thay `lookup_values` DJ-HRM 1-1 |
| `Common_Codes_Data.sql` | ~12 KB | Bản SQL của common codes | Tham chiếu |
| `GenuiSuite_Code.sql` | ~171 KB | Mã/procedure phía GenusSuite | Tham chiếu logic cũ |
| `GenuiSuite_Logic.sql` | ~745 KB | Logic PL/SQL lớn | Tham chiếu công thức / nghiệp vụ |
| `HR_Config_Data.sql` | **0 byte** | Trống | Bỏ qua |
| `LabourContract_SW.doc` | ~86 KB | Mẫu Word HĐ | In ấn / tham chiếu mẫu |
| `rptAppliLeter.DOC` | ~15 KB | Mẫu đơn | Tham chiếu |

### Mã HR hay gặp trong `Common_Codes.csv` (đã thấy)

| Code group | Ý nghĩa |
|------------|---------|
| `HRAB0010` | Trạng thái NV: A Active / R Resign / S Stop |
| `HRAB0030` | Loại HĐ: `1`=HD1, `3`=VTH, `0`=TV, `2`=HD2 |
| `HRAB0040` | Group Code (ACCOUNTANT, LINE F, PACKING, …) |
| `COAB0080` | Nation: VIE, KOR, MYA, US, CHN, JAP |

→ DJ-HRM đã có `lookup_values` (34 đơn vị hành chính, dân tộc, tôn giáo…) — **không** import nguyên Common_Codes vào UI.

---

## 3. `Salary/` (tham chiếu nhanh — cùng đợt quét)

File dạng `2.Salary table for {Month}.2026.xls` (Jan…July).

Có: MSNV, họ tên, CCCD, số TK (hoặc SĐT nếu ≤11 số bắt đầu 0), tổ, chức vụ, ngày vào, ngày ký HĐ, lương TV/HĐ, giới tính, ATM/CASH.

**Không có:** địa chỉ, nơi sinh, dân tộc, hôn nhân.

Script an toàn chỉ điền STK trống:

```powershell
docker cp "D:/dj-hrm/dj-hrm/HIEN_PHAP/Salary" djhrm-api:/tmp/salary_dir
docker compose exec api python -m app.scripts.fill_bank_from_salary /tmp/salary_dir --latest
```

---

## 4. Ánh xạ học vấn Excel → DJ-HRM

| Text / legacy | `education_code` |
|----------------|------------------|
| University | `EDUCATION_LEVEL008` (Đại học) |
| Intermediate (2 years) / TC2 | `EDUCATION_LEVEL006` (Trung cấp) |
| 12/12 / `12` | `EDUCATION_LEVEL004` (THPT) |
| 9/12 | `EDUCATION_LEVEL003` (THCS) |
| under 9 | `EDUCATION_LEVEL002` (Tiểu học) |

Nơi sinh/cấp: text tỉnh (vd. `Tây Ninh`) → `BIRTH_PLACE030` / `ID_ISSUE_PLACE030` (danh sách 34 đơn vị trong `lookup_seed.py`).

---

## 5. Việc còn lại nếu có nguồn mới

1. Export GenusSuite **THR_ABEMP** (hoặc Excel đủ cột dân tộc / hôn nhân / tạm trú / người thân) → mới điền các trường đang = 0.
2. ~74 NV tên lỗi font: không có trong file 11.08 — cần danh sách bổ sung hoặc backup UTF-8 từ máy công ty.
3. Phụ cấp POS/TOXIC/… từ file 1.2 → bảng phụ cấp (phiên riêng, có test).

---

*File này là chỉ mục sau khi quét — không thay thế hiến pháp 20–24. Cập nhật ngày ở đầu file nếu quét lại nguồn mới.*
