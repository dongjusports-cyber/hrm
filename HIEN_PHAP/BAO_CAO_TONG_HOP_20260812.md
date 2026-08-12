# Báo cáo tổng hợp phiên 2026-08-12 — DJ-HRM

> **Ngày:** 2026-08-12 (buổi tối)  
> **Mục đích:** Bàn giao đầy đủ backend + UI + test; hướng dẫn **Cursor Pro Cloud Agent** kiểm tra bug  
> **Repo:** `D:\dj-hrm\dj-hrm` · nhánh `main`  
> **Đăng nhập UAT:** `hr.demo` / `HrDemo@123456` · viewport **1366×768** và **1920×1080**

---

## 0. Tóm tắt điều hành

| Hạng mục | Trạng thái |
|----------|------------|
| API pytest | **346/346 pass** (phiên trước; xác nhận lại trước release) |
| Web vitest | **25/25 pass** (gồm `aiFabPosition`, `disabledHint`, `formatDate`) |
| Bug P0 lương (1604/1718/TOXIC) | **Code đã sửa** · DB công ty **chưa Tính lương lại** |
| UI audit §23 (U1–U7, P3) | **Đã code** — commit phiên này |
| Git | **Commit + push** cho cloud agent test |

**Kết luận:** Backend nghiệp vụ và test ổn định; UI đã đóng backlog audit P0–P3. Việc còn lại chủ yếu là **Ops UAT trên DB thật** (Tính lương lại kỳ 2026-08) và xác nhận MSNV 1604/1718/1519.

---

## 1. Backend — bug & nghiệp vụ (đã có trên repo)

Chi tiết: **`BAO_CAO_BUG_FAIL_20260812_PM.md`**

### 1.1 P0 — Lương

| Bug | Sửa | File chính |
|-----|-----|------------|
| NV nghỉ vẫn trên bảng lương (1604, 1718) | Lọc `period_eligibility` + purge phiếu nháp | `payroll/period_eligibility.py`, `service.py` |
| Xóa TOXIC trên hồ sơ nhưng Tính lương vẫn có (1519) | Bỏ `seed_fixture_allowance_assignments` khỏi `calculate_period` | `payroll/service.py` |

### 1.2 OT split (Hiến pháp §22)

- Chỉ tính OT khi bấm ra **sau 17:15**; phút OT tính từ 17:00.
- **T3/T5** → OT trên sổ; ngày khác → OT ngoài (`OT_EXT`).
- Ghi trong `22_QUY_TAC_NGHIEP_VU.md` (khóa `ot_split` trong policy payload).

### 1.3 Test đồng bộ (7 fail → 0)

- `test_attendance_days`, `test_attendance_days_extend_34`, `test_attendance_punch_dedupe_32`, `test_timesheet*`, `test_payroll_resign_rehire`, `test_payroll_period_eligibility`, `test_ot_split`, `test_ot_external_pay`.

### 1.4 Commit phiên này (API nhỏ)

| Thay đổi | File |
|----------|------|
| Lookup `marital_status` (single, married, divorced, widowed) | `mdm/lookup_seed.py` |
| Test 7 nhóm lookup | `tests/test_lookup_values.py` |

---

## 2. Frontend — UI audit P0 → P3 (commit phiên này)

Chi tiết audit gốc: **`BAO_CAO_UI_UX_20260812_PM.md`** · backlog §23.11: **`23_UI_MAN_HINH.md`**

### P0 — Critical

| ID | Việc | File |
|----|------|------|
| U1 | FAB AI không che lưới — `nudgeFabFromGrid`, nút ↺ reset | `AiFab.tsx`, `aiFabPosition.ts` |
| U2 | Dropdown phụ cấp chỉ `allowance_types`, placeholder «— Chọn loại phụ cấp —» | `EmployeeProfileFields.tsx`, `EmployeeProfileSheet.tsx` |
| U3 | Mở hồ sơ: cột Xem, double-click dòng, click MSNV/Họ tên | `EmployeesPage.tsx` |

### P1 — Toolbar & lưới §23.1–23.2

| Việc | File |
|------|------|
| HR toolbar ≤46px, menu **⋮ Thêm**, status bar 32px | `EmployeesPage.tsx`, `global.css`, `ToolbarMoreMenu.tsx` |
| Payroll toolbar gọn + ⋮ (xuất Excel, admin) | `PayrollPage.tsx` |
| Chấm công toolbar gọn + ⋮ + status bar | `TimekeepingPage.tsx` |
| Tìm MSNV xuất lương (combobox thay `<select>` 357 option) | `EmployeeCodePicker.tsx` |
| Cột tiền canh phải `tabular-nums`; Loại HĐ/Tài khoản rộng hơn | `EmployeesPage.tsx`, `payrollGridColumns.ts`, `global.css` |

### P2 — Polish

| Việc | File |
|------|------|
| Chấm công: bỏ split 50/50 — 7 tab full-width | `TimekeepingPage.tsx` |
| Tooltip cột AL/REM/OT trên lưới tháng | `TimekeepingPage.tsx` |
| Cột Δ lương: đỏ chỉ khi \|Δ\| ≥ 500k; 0 = xám | `PayrollPage.tsx`, `payrollGridColumns.ts` |
| Tooltip nút disabled | `disabledHint.ts` — HR, Payroll, Timekeeping |
| Status bar payroll (số phiếu, trạng thái kỳ) | `PayrollPage.tsx` |

### P3 — Portal & phím tắt

| Việc | File |
|------|------|
| Portal HUD: gợi ý + nút HR / Ctrl+K | `PortalHome.tsx` |
| Hint `/`, Ctrl+K, Esc, F2; `/` focus ô tìm | `KeyboardHintsBar.tsx`, `App.tsx`, `CommandPalette.tsx` |
| Tình trạng hôn nhân → `LookupSelect` + seed backend | `EmployeeProfileFields.tsx`, `LookupSelect.tsx` |

### Component dùng chung mới

```
apps/web/src/shared/ToolbarMoreMenu.tsx
apps/web/src/shared/EmployeeCodePicker.tsx
apps/web/src/shared/KeyboardHintsBar.tsx
apps/web/src/shared/disabledHint.ts (+ test)
```

---

## 3. Kết quả test

```powershell
cd apps\web && npm run test -- --run
# → 25 passed (6 files)

cd apps\api && python -m pytest tests/ -q
# → 346 passed (phiên trước; chạy lại trước merge production)

cd apps\api && python -m pytest tests/test_lookup_values.py tests/test_ot_external_pay.py tests/test_ot_split.py tests/test_payroll_export.py -q
# → 20 passed (phiên commit)
```

---

## 4. Việc Ops — chưa làm (cần người vận hành)

- [ ] Portal → **Tính lương** kỳ **2026-08** → **Tính lương lại**
- [ ] MSNV **1604**, **1718**: không còn trên lưới hoặc không âm vô lý
- [ ] MSNV **1519**: xóa TOXIC (nếu còn) → Lưu → Tính lương → không tự hiện lại
- [ ] (Tuỳ chọn) Revert `phone = 0901234567` trên 1519 sau UAT UI

---

## 5. Hướng dẫn Cloud Agent — kiểm tra bug

### 5.1 Môi trường

```powershell
cd D:\dj-hrm\dj-hrm
docker compose up -d
# Web: http://localhost:5173
# API: http://localhost:8000/health
```

### 5.2 Checklist UAT (ưu tiên)

| # | Màn | Thao tác | Kỳ vọng |
|---|-----|----------|---------|
| 1 | HR `/m/hr/lists/all` | Viewport 1366×768 — đo toolbar | ≤46px, không wrap 2 hàng |
| 2 | HR | Double-click dòng / nút Xem / click MSNV | Mở overlay hồ sơ |
| 3 | HR | Tab Phụ cấp → Thêm | Dropdown không mặc định «Điều chỉnh» |
| 4 | Mọi lưới staff | Kéo FAB AI vào vùng grid | FAB tự né hoặc ↺ reset |
| 5 | Lương `/m/payroll` | Toolbar + ⋮ + EmployeeCodePicker | Một hàng; tìm MSNV gõ được |
| 6 | Lương | Cột Δ — so sánh \|Δ\| < 500k vs ≥ 500k | Màu xám vs đỏ |
| 7 | Chấm công | 7 tab full-width, không split | Tab chuyển mượt |
| 8 | Portal | HUD + KeyboardHintsBar | Nút HR, hint phím tắt |
| 9 | Hồ sơ NV | Tình trạng hôn nhân | Dropdown lookup, không gõ tự do |
| 10 | Lương kỳ 2026-08 | **Tính lương lại** (admin) | 1604/1718 biến mất nếu đã nghỉ |

### 5.3 Regression tự động

```powershell
cd apps\api && python -m pytest tests/ -q
cd apps\web && npm run test -- --run
```

### 5.4 Known deferrals (không coi là bug phiên này)

- Tab **Hợp đồng** trong overlay hồ sơ — Link có thể đóng sheet (refactor lớn).
- Nút **Toàn màn hình** — giữ thử nghiệm, có tooltip.
- Tìm NV inline trên Portal — P3 chỉ shortcut; full search = backlog sau.

---

## 6. Tài liệu tham chiếu

| File | Nội dung |
|------|----------|
| `BAN_GIAO_PHIEN_20260812.md` | Checklist bàn giao (cập nhật sau commit) |
| `BAO_CAO_BUG_FAIL_20260812_PM.md` | Bug backend + 346 pytest |
| `BAO_CAO_UI_UX_20260812_PM.md` | Audit UI gốc (trước code) |
| `22_QUY_TAC_NGHIEP_VU.md` | OT split, policy |
| `23_UI_MAN_HINH.md` §23.11 | Backlog U1–U7 Done |

---

## 7. Prompt gợi ý cho Cloud Agent

```
Đọc HIEN_PHAP/BAO_CAO_TONG_HOP_20260812.md §5.
Checkout main mới nhất, docker compose up, đăng nhập hr.demo.
Chạy pytest + vitest. UAT checklist §5.2 trên viewport 1366×768.
Báo bug theo mẫu BAO_CAO_BUG_FAIL (mức P0/P1, file, bước tái hiện).
Ưu tiên: Tính lương lại 2026-08 và xác nhận MSNV 1604/1718/1519.
```

---

*Báo cáo tổng hợp — 2026-08-12 23:50 · Push GitHub cho Cursor Pro Cloud Agent test.*
