# Báo cáo bàn giao — phiên làm việc máy nhà · 2026-08-10

> Đọc file này **trước** khi tiếp tục code trên máy công ty.
> Chủ: Nguyễn Thanh Thiện · AI máy nhà: Cursor Grok · AI máy công ty: Cursor Pro

---

## 0. Quy ước nguồn khi thiếu thông tin (đã chốt với Chủ)

Thứ tự ưu tiên (cao → thấp), khớp `20_HIEN_PHAP_V2_QUY_TRINH.md` §20.0:

1. Lời Chủ trong chat (mới nhất thắng)
2. Bộ Hiến pháp V2 (`HIEN_PHAP/20`–`24`)
3. Bộ Hiến pháp V1 (`HIEN_PHAP/00`–`15`) — phần V2 không nhắc tới
4. **File gốc GenusSuite** trong `HIEN_PHAP/GenuSuite HRM/` (và `Salary/`, `Amis/` khi cần)
5. Mã nguồn hiện tại

**Khi hiến pháp thiếu chi tiết nghiệp vụ → mở thẳng file SQL/Excel trong `HIEN_PHAP/GenuSuite HRM/`, không đoán.**

---

## 1. Trả lời câu hỏi: `AllowanceType` → `PayComponent` đổi vì sao?

**Đổi theo Hiến pháp V2, KHÔNG đổi để giống GenusSuite.**

| Nguồn | Tên / ý nghĩa |
|-------|----------------|
| Hiến pháp V1 (`07_SCHEMA`) | `allowance_types` — chỉ nghĩ tới **phụ cấp** |
| Hiến pháp V2 (`21§21.4`, hạng mục **2.3** trong `24`) | Đổi tên → `pay_components`, thêm 5 cột cờ, nạp ~30 mã |
| GenusSuite | Không có bảng tên `PayComponent`. Có ~148 cột trong bảng lương (`THR_SALARY_EMP`…) trộn phụ cấp + khấu trừ + info. GenusSuite cũng có `TCO_ABCODE` (2.609 mã trộn 427 nhóm) — **đó là cái V2 cấm lặp lại** |

**Vì sao phải đổi tên (theo V2):**
- `allowance_types` = “loại phụ cấp” → hẹp, không chứa khoản **khấu trừ** (BHXH, thuế, công đoàn…) và khoản **info**.
- `pay_components` = “khoản lương” (earning | deduction | info) — đúng phạm vi engine lương đợt 4 sẽ dùng (`payslip_components.component_code` FK sang đây).
- Hiến pháp ghi rõ: **đổi tên bảng, giữ dữ liệu, thêm cột** — không tạo bảng song song (`21§21.1` mục “Lưu ý dễ nhầm”).

**Alias tương thích:** trong code còn `AllowanceType = PayComponent` để không đập script cũ (N1).

---

## 2. Trạng thái lộ trình (máy nhà · 2026-08-10)

### ĐỢT 1 — Cây tổ chức → **ĐÓNG**

| Mã | Hạng mục | Trạng thái |
|----|----------|------------|
| 1.1 | Model + migration tổ chức | ✅ (trước đó) |
| 1.2 | Script dựng cây tổ chức | ✅ chạy lại trên máy nhà |
| 1.3 | Nạp lương GenusSuite Jan–Jul/2026 | ✅ 438 NV, 2.133 phiếu, 0 NV thiếu tổ |
| 1.4 | API + lưới NV (lọc Bộ phận › Tổ, Excel) | ✅ |
| 1.5 | `employee_assignments` + chuyển tổ hàng loạt | ✅ |
| Dọn #5 | Bỏ `employees.department_id` | ✅ migration `0025` |

**Nghiệm thu đợt 1 (5/5):** đúng 10 bộ phận / 73 tổ / 438 NV; lọc Sewing → tổ con đúng; snapshot tổ tháng 3 ≠ tổ hiện tại; không còn cột `employees.department_id`.

### ĐỢT 2 — Danh mục & chính sách → **XONG (code máy nhà)**

### ĐỢT 3 — Chấm công → **đang làm** (3.1 xong)

| Mã | Hạng mục | Trạng thái máy nhà |
|----|----------|-------------------|
| **2.1** | `lookup_values` | ✅ xong |
| **2.2** | `leave_types` mở rộng (14 mã + cờ) | ✅ xong (migration `0027`) |
| **2.3** | `pay_components` (đổi tên + 5 cột + catalog) | ✅ xong (migration `0028`) |
| **2.4** | `work_shifts` + `team_shift_schedules` | ✅ model/migration/`seed` có (`0029`) — **cần Pro kiểm tra nghiệm thu + báo cáo 20.6** |
| **2.5** | Bảng chính sách có ngày hiệu lực | ✅ xong (migration `0030`) — 5 bảng + API đọc + test 136 tháng = 550.000 |
| **2.6** | Mở rộng `policy_packages.payload` | ✅ (máy nhà 2026-08-10) |
| **2.7** | `roles` + `role_permissions` | ✅ migration `0031`, API `/api/config/roles`, seed `hr_staff` / `payroll_accountant` |
| **2.8** | Màn Admin › Danh mục + Gói chính sách | ✅ API `/api/config/catalog/*`, UI `catalogs` + `policy-package` |

**Migration mới (máy nhà, chưa chắc đã apply ở công ty):**

```
20260810_0024_employee_assignments.py
20260810_0025_drop_employees_department_id.py
20260810_0026_lookup_values.py
20260810_0027_leave_types_expand.py
20260810_0028_pay_components_rename.py
20260810_0029_work_shifts.py
20260810_0030_policy_rate_tables.py
20260810_0031_roles_role_permissions.py
20260810_0032_attendance_punches_extend.py
```

### ĐỢT 3 — Chấm công (bắt đầu)

| Mã | Hạng mục | Trạng thái máy nhà |
|----|----------|-------------------|
| **3.1** | `attendance_punches` mở rộng | ✅ migration `0032`, `employee_id`/`direction`/`sync_job_id` lúc nạp; GET unlinked, POST relink |

**Test backend máy nhà lần cuối:** **181 passed** (`pytest -q`). **Máy công ty:** `alembic upgrade head` (tới `0032`) rồi chạy lại pytest; **đọc thêm** `HIEN_PHAP/HUONG_DAN_USB_VA_MAY_CONG_TY_20260811.md`.

---

## 3. File đã tạo / sửa chính (theo hạng mục)

### Khôi phục dữ liệu máy nhà (không phải feature mới)
- Chạy lại `python -m app.scripts.load_org_structure` (1.2)
- Chạy lại `python -m app.scripts.import_genussuite_2026` (1.3)
- **CẢNH BÁO máy công ty:** DB công ty nếu còn 438 NV thật thì **KHÔNG chạy lại** 1.2/1.3 — hai script xóa sạch employees/payslips trước khi nạp.

### 1.5 — `employee_assignments`
- `app/modules/mdm/models.py` — model `EmployeeAssignment`
- `alembic/.../0024_employee_assignments.py`
- `service.py` / `router.py` / `schemas.py` — preview + apply chuyển tổ hàng loạt
- `apps/web/.../TransferTeamModal.tsx` + checkbox lưới NV
- `tests/test_transfer_team.py`

### Dọn đợt 1 — bỏ `employees.department_id`
- Model: `department_id` / `department` thành **hybrid_property** suy từ `team`
- Migration `0025` (kiểm tra không lệch dữ liệu rồi mới drop cột)
- Form tạo/sửa NV: bắt buộc chọn **Tổ**; Bộ phận chỉ để lọc
- Import Excel: thêm `team_code`
- Script GenusSuite: bỏ ghi `department_id`

### 2.1 — `lookup_values`
- `app/modules/mdm/models.py` — `LookupValue`
- `app/modules/mdm/lookup_seed.py` — 6 nhóm seed
- Migration `0026`
- API: `GET /api/lookup-values`, `GET /api/lookup-groups`
- `tests/test_lookup_values.py`
- **Lệch cần Chủ:** `birth_place` / `id_issue_place` seed theo **63 tỉnh trước sáp nhập 2025** — chưa đủ chắc để tự suy danh sách sau sáp nhập.

### 2.2 — `leave_types` mở rộng
- Migration `0027` + mở rộng model/seed trong `attendance/`
- `pay_ratio_percent` NULL riêng cho `PER` (bắt buộc HR khai — đúng 24§2.2)

### 2.3 — `pay_components`
- Migration `0028`: rename `allowance_types` → `pay_components`, thêm 5 cột
- Model `PayComponent` (+ alias `AllowanceType`)
- Catalog mở rộng trong `seed_allowances.py` (mã suy từ cột GenusSuite, có comment nguồn)

### 2.4 — `work_shifts`
- Migration `0029`, model `WorkShift` + `TeamShiftSchedule`
- `seed_shifts.py` — ca hành chính 08:00–17:00
- `teams.default_shift_id` (FK theo code)
- Service/API trong `attendance/shifts_service.py`

### 2.5 — Bảng chính sách có ngày hiệu lực
- Migration `0030`: `insurance_rates`, `pit_brackets`, `pit_deductions`, `seniority_allowance_tiers`, `attendance_bonus_rules`
- Seed từ 22§ + GenusSuite `F_CAL_SERVERANCE` / `F_CAL_INDUS_AMT` (`seed_rates.py`)
- API đọc: `/api/policies/insurance-rates/current`, `pit-brackets`, `pit-deductions/current`, `seniority-tiers`, `seniority-amount?months=`, `attendance-bonus-rules/current`
- Test: **136 tháng → 550.000** ✔; 18 tháng → 75.000; chuyên cần 600.000 + ngưỡng 3/2/5/4
- **Lệch:** cột `union_pct` (tên 21) thực tế chứa **44.100đ cố định** (GenusSuite); `region_min_wage` seed 4.960.000 (NĐ 74/2024 vùng I) — GenusSuite không có cột này, cần Chủ xác nhận nếu công ty áp vùng khác

### Fix phụ (trước 1.5)
- `seed_portal_tabs` **không còn ghi đè** tên tab Admin đã đổi
- Test worker dùng `DEFAULT_WORKER_PASSWORD` (`1234`) thay `"Worker@123456"`

---

## 4. Việc Cursor Pro ở công ty nên làm ngay

1. **Copy code** từ máy nhà → máy công ty (không copy `.venv`, `node_modules`, `.env`, DB).
2. Trong `apps/api`:  
   `alembic upgrade head`  
   *(chỉ migration — **không** chạy lại `load_org_structure` / `import_genussuite_2026` nếu DB công ty còn dữ liệu thật.)*
3. Chạy:  
   `python -m pytest -q`  
   Ghi lại số passed/failed.
4. Đọc lại báo cáo này + mẫu `20§20.6`.
5. **Tiếp tục đúng một mã:** kiểm tra/đóng 2.4 nếu còn sót, rồi sang **2.5** (bảng chính sách có `effective_from` / `effective_to`). Không gộp nhiều hạng mục trong một phiên (24§0).
6. Khi thiếu số liệu nghiệp vụ → mở `HIEN_PHAP/GenuSuite HRM/`, không đoán.

---

## 5. Việc còn treo / cần Chủ

| Việc | Ghi chú |
|------|---------|
| Git init + remote private | Chủ hẹn làm tối trước khi nghỉ — **chưa làm** trên máy nhà (repo chưa có `.git`) |
| Danh sách tỉnh/thành sau sáp nhập 2025 | Cho vào `lookup_values` (birth_place / id_issue_place) khi Chủ cung cấp |
| `pay_components` ~30 mã | Catalog hiện ~20 mã “đúng nguồn”; phần cột GenusSuite còn lại thuộc công/OT/nghỉ (bảng khác) — HR thêm qua 2.8 nếu thiếu khoản thật |
| CRUD Admin cho lookup / leave / pay / shift | Thuộc **2.8**, chưa làm |

---

## 6. Lệnh tham chiếu nhanh (máy nhà đã dùng)

```powershell
# API
cd D:\dj-hrm\apps\api
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest -q

# Web
cd D:\dj-hrm\apps\web
npx tsc --noEmit
npm run build
```

---

*Hết báo cáo bàn giao máy nhà 2026-08-10. Việc tiếp theo đề xuất: nghiệm thu 2.4 (nếu cần) → 2.5.*
