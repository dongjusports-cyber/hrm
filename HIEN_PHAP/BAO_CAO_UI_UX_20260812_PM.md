# Báo cáo rà soát UI/UX — gửi Kiến trúc sư trưởng DJ-HRM

> **Phiên:** 2026-08-12 (buổi tối, sau báo cáo bug/test)  
> **Người lập:** Cursor AI (theo chỉ đạo Chủ phần mềm)  
> **Đối tượng:** Kiến trúc sư trưởng phát triển phần mềm DJ-HRM  
> **Chuẩn đối chiếu:** `23_UI_MAN_HINH.md` §23.1–23.3  
> **Phương pháp:** Đăng nhập `hr.demo` · viewport **1920×1080** và **1366×768** · thao tác lặp như HR lâu năm (lọc, mở hồ sơ, tab, sửa/lưu, chấm công, lương)  
> **Trạng thái code UI:** **chưa sửa** trong phiên này — chỉ audit + ghi Hiến pháp

---

## 0. Tóm tắt điều hành

| Tiêu chí | Đánh giá |
|----------|----------|
| Lưới AG Grid (HR / Lương / Chấm công) | **Đạt** — cuộn trong grid, không cuộn cả trang (1920) |
| Hồ sơ NV overlay + Lưu | **Đạt** — tab mượt, lưu không nhảy trang |
| Toolbar một hàng (§23.1 ≤46px) | **Chưa đạt** — HR 92px, Lương 79px, Chấm công 57px+ trên 1366 |
| Nút Trợ Lý AI | **Lỗi P0** — che cột dữ liệu lưới |
| Dropdown phụ cấp hồ sơ NV | **Lỗi P0** — mặc định khoản lương, dễ thêm nhầm |
| Mở hồ sơ từ danh sách | **Chưa tiện** — chỉ bấm cột Họ tên |

**Kết luận kiến trúc:** Chức năng core ổn; **chrome toolbar** và **FAB AI** là khoảng cách lớn nhất so với Hiến pháp §23 và tiêu chí “HR làm nhanh trên laptop 1366”. Backend bug lương đã sửa phiên trước nhưng **DB công ty chưa Tính lương lại** → UI vẫn thấy 1604/1718 âm tiền.

---

## 1. Phương pháp kiểm tra

1. `http://localhost:5173` — user `hr.demo` / `HrDemo@123456`
2. Màn đã test: Portal · HR danh sách · Hồ sơ MSNV 1519 · Chấm công · Tính lương kỳ 2026-08
3. Đo layout bằng CDP: chiều cao toolbar, `body.scrollHeight`, wrap toolbar
4. Thao tác lặp: Tìm 1519 → tab Kinh nghiệm → về Hồ sơ chính → sửa SĐT → Lưu hồ sơ

**Dữ liệu test để lại:** MSNV **1519** — trường **Điện thoại = `0901234567`** (lưu thử). Phiên sau có thể xóa hoặc giữ.

---

## 2. Lỗi / thiếu sót theo mức ưu tiên

### P0 — Sửa trước (che dữ liệu / gây nhầm nghiệp vụ)

| # | Màn | Vấn đề | File gợi ý |
|---|-----|--------|------------|
| U1 | Mọi lưới staff | Nút **Trợ Lý AI** (kéo thả, nhớ `localStorage`) đè lên cột Họ tên / BP | `apps/web/src/shared/AiFab.tsx`, `aiFabPosition.ts` |
| U2 | Hồ sơ NV | Dropdown **Thêm phụ cấp** mặc định «Điều chỉnh (truy lĩnh / trừ khác)» — là khoản **lương**, không phải allowance | `EmployeeProfileFields.tsx`, `EmployeeProfileSheet.tsx` |
| U3 | HR danh sách | Mở hồ sơ **chỉ** khi click cột `full_name`; click MSNV / dòng khác không mở | `EmployeesPage.tsx` `onCellClicked` |

**Đề xuất U1:** FAB mặc định góc dưới-phải; khi mở panel auto dời; nút «Đặt lại vị trí»; optional snap tránh vùng grid.

**Đề xuất U2:** Chỉ list `allowance_types`; placeholder «— Chọn loại phụ cấp —»; tách hẳn khỏi pay adjustment codes.

**Đề xuất U3:** Double-click dòng → mở overlay; hoặc thêm cột/nút **Xem** (giống Chấm công).

---

### P1 — Layout / §23.1 (1366×768 — laptop HR)

| Màn | Toolbar đo được | Chuẩn 46px | Nguyên nhân |
|-----|-----------------|------------|-------------|
| HR danh sách | **92px** (2 hàng) | ❌ | `.hr-toolbar { flex-wrap: wrap }` + >10 nút/hàng |
| Tính lương | **79px** (2 hàng) | ❌ | Kỳ + 4 nút kỳ + 2 dropdown xuất + 3 nút xuất file |
| Chấm công | **57px** + dòng status | ❌ | `.tk-toolbar` + banner sync |

**Hậu quả:** Mất ~4–6 dòng lưới so với ngân sách chrome 160px (§23.1).

**Đề xuất (theo §23.1):**
- Tối đa **4 bộ lọc + Tìm** trên một hàng; còn lại → **«Lọc nâng cao»** (sheet/trượt)
- Nút phụ (Nhập Excel, Đặt lại cột, …) → menu **«⋮ Thêm»**
- Hàng **Chuyển tổ / Tăng lương / Nhập Excel** → **status bar** 32px (§23.1)
- CSS: `flex-wrap: nowrap` + `overflow-x: auto` trên toolbar thay vì wrap

**File CSS chính:** `apps/web/src/styles/global.css` — `.hr-toolbar`, `.payroll-toolbar-*`, `.tk-toolbar`

---

### P1 — Lưới dữ liệu (§23.2)

| Vấn đề | Chi tiết |
|--------|----------|
| Cột cắt chữ | «Loại HĐ» → «Vô thời hạn (V…»; «Tài khoản» → «Hoạ…» / «Nghỉ…» |
| Cột tiền | «Lương Tổng» canh **trái** — §23.2 yêu cầu canh phải + `tabular-nums` |
| Cột cuối HR | «Bảo mật» bị cắt trên 1366 — cần scroll ngang hoặc thu cột |

**File:** `EmployeesPage.tsx` (colDef), theme AG Grid trong `global.css`

---

### P2 — Theo module

#### Nhân sự — Danh sách
- **Tốt:** Lọc BP/Tổ, Gọn/Đầy đủ, grid full chiều cao (1920), không scroll trang
- **Chưa tốt:** Nút disabled (Chuyển tổ, Tăng lương) không tooltip; Nhập Excel trông giống nút thường; thiếu **status bar** đếm bản ghi; NV 1604 hiện ngày vào **12/08/2026** (dữ liệu)

#### Hồ sơ NV (overlay)
- **Tốt:** 5 cột một màn 1366; header/tab cố định; Lưu disable form; toast; Esc; Ctrl+Z; không nhảy scroll khi Lưu
- **Chưa tốt:** Tab **Hợp đồng** = `Link` route mới → mất overlay; checkbox BHXH/Thuế readonly không giải thích; tab Kinh nghiệm cuộn nhẹ trong vùng con (~50px) — chấp nhận được

#### Chấm công
- **Tốt:** Kỳ 2026-08; tab Tổng hợp / Bảng ngày / Rà soát; nút Xem rõ
- **Chưa tốt:** Split 50/50 → **2 vùng cuộn**; 7 tab phụ + 6 nút; panel Bảng ngày quá nhiều control một hàng; mã cột AL/REM/OT sổ cần tooltip

#### Tính lương
- **Tốt:** Tab chế độ xem mượt; filter Xuất BP/1 người; status bar tổng kỳ
- **Chưa tốt:** Cột Δ toàn đỏ (noise); dropdown Xuất 1 người **357 option** — cần ô tìm MSNV; **1604 (−46M), 1718 (−664k)** vẫn hiện — cần **Tính lương lại** sau fix backend

---

### P3 — Polish

| Mục | Ghi chú |
|-----|---------|
| Nút Toàn màn hình | Góc phải — thử nghiệm, chưa §23 |
| Portal khay «CHI TIẾT NHÂN SỰ» | Placeholder rỗng lần đầu vào |
| Phím tắt §23.2 | `/`, F2, Ctrl+K — chưa hint trên UI |
| `marital_status` | Text tự do — §23.3 nên lookup |
| Tooltip nút disabled | Toàn app |

---

## 3. Điểm đạt chuẩn (giữ nguyên)

1. **FullScreenSheet** — lock body scroll, toast overlay
2. **Kỳ mặc định** — `currentPayPeriod()` trên Portal modules
3. **Grid-first** trên 1920 — vùng dữ liệu chiếm phần lớn viewport
4. **Luồng Lưu hồ sơ** — ổn định, không reload / nhảy màn hình
5. **Xuất lương theo BP / 1 MSNV** — đúng nhu cầu HR

---

## 4. Thứ tự sửa đề xuất (1–2 phiên UI)

| Bước | Việc | Effort |
|------|------|--------|
| 1 | FAB AI không che grid (U1) | S |
| 2 | Dropdown phụ cấp + double-click hồ sơ (U2, U3) | S |
| 3 | Toolbar HR + Lương một hàng + menu ⋮ (P1) | M |
| 4 | ColDef: width tiền canh phải, Loại HĐ/Tài khoản (P1) | S |
| 5 | Chấm công: gom tab phụ / giảm split (P2) | L |
| 6 | UAT: Tính lương lại 2026-08 trên DB công ty | Ops |

---

## 5. Liên kết phiên trước (backend)

Báo cáo bug/test: **`BAO_CAO_BUG_FAIL_20260812_PM.md`**

| Backend đã sửa | UI vẫn cần |
|----------------|------------|
| Lọc NV nghỉ khỏi calculate | **Tính lương lại** kỳ mở trên DB thật |
| Bỏ seed TOXIC khi calculate | UAT MSNV 1519 trên UI |
| 346/346 pytest pass | Không đổi |

---

## 6. Lệnh kiểm tra nhanh (phiên sau)

```powershell
# Web dev (nếu chưa chạy)
cd D:\dj-hrm\dj-hrm
docker compose ps

# UI manual
# http://localhost:5173/login → hr.demo
# HR: /m/hr/lists/all
# Lương: /m/payroll
# Chấm công: /m/timekeeping
# Hồ sơ test: /m/hr/employees/67f87371-a211-426e-8b40-ba9876f92d74
```

Viewport test 1366×768: DevTools hoặc resize — toolbar HR phải ≤46px sau khi sửa.

---

*Báo cáo này là nguồn chính thức cho audit UI/UX phiên 2026-08-12 trong `HIEN_PHAP/`.*
