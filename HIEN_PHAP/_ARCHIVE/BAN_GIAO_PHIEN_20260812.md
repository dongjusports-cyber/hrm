# Bàn giao phiên 2026-08-12 → phiên chat tiếp theo

> **Mục đích:** AI/Developer mở phiên mới đọc file này **trước**, rồi đọc chi tiết theo link.  
> **Working tree:** UI P0–P3 + lookup marital_status · **đã commit + push** (cloud agent test)  
> **Repo:** `D:\dj-hrm\dj-hrm`

---

## 1. Đọc theo thứ tự (3 phút)

| # | File | Nội dung |
|---|------|----------|
| 1 | **`BAN_GIAO_PHIEN_20260812.md`** | File này — checklist tổng |
| 2 | **`BAO_CAO_BUG_FAIL_20260812_PM.md`** | Bug P0 lương + 7 test → 346 pass |
| 3 | **`BAO_CAO_UI_UX_20260812_PM.md`** | Audit UI/UX — **chưa code** |
| 4 | `20_HIEN_PHAP_V2_QUY_TRINH.md` | Quy trình V2 |
| 5 | `23_UI_MAN_HINH.md` §23.7 | Backlog UI phiên 12/08 |

---

## 2. Trạng thái hiện tại

| Hạng mục | Trạng thái |
|----------|------------|
| API pytest | **346/346 pass** |
| Web vitest | **25/25 pass** |
| Docker | `api`, `web`, `postgres`, `redis` — Up |
| Bug P0 lương (1604/1718/TOXIC) | **Code đã sửa** · DB công ty **chưa Tính lương lại** |
| UI/UX §23 (U1–U7, P3) | **Đã code** — xem `BAO_CAO_TONG_HOP_20260812.md` |
| Git | **Đã push** `main` — cloud agent test |

---

## 3. Việc ưu tiên cho phiên tiếp (Chủ chưa chỉ định — đề xuất)

### A. Nghiệm vụ (Ops — 15 phút)
- [ ] Đăng nhập Portal → **Tính lương** kỳ **2026-08** → **Tính lương lại**
- [ ] Xác nhận MSNV **1604**, **1718** biến mất hoặc không còn âm vô lý
- [ ] MSNV **1519**: xóa TOXIC (nếu còn) → Lưu → Tính lương → không tự hiện lại

### B. UI P0 (code — phiên riêng hoặc gộp)
- [ ] **U1** FAB AI không che lưới — `AiFab.tsx`, `aiFabPosition.ts`
- [ ] **U2** Dropdown phụ cấp hồ sơ — chỉ `allowance_types` — `EmployeeProfileFields.tsx`
- [ ] **U3** Double-click / nút Xem mở hồ sơ — `EmployeesPage.tsx`

### C. UI P1 (toolbar §23.1)
- [ ] HR toolbar 1 hàng + menu ⋮ — `global.css` `.hr-toolbar`, `EmployeesPage.tsx`
- [ ] Payroll toolbar gọn — `PayrollPage.tsx`, `.payroll-toolbar-*`
- [ ] Cột tiền canh phải AG Grid — `EmployeesPage.tsx` colDef

### D. Hiến pháp văn bản
- [ ] Bổ sung **§ OT split** vào `22_QUY_TAC_NGHIEP_VU.md` (17:15, T3/T5, OT_EXT)
- [ ] (Tuỳ chọn) Ghi nút Toàn màn hình vào `23_UI_MAN_HINH.md` nếu Chủ giữ

### E. Git (chỉ khi Chủ yêu cầu)
- [ ] Commit gói: payroll eligibility + TOXIC fix + ot_split tests + pay period + export filters
- [ ] Commit riêng UI nếu làm xong P0/P1

---

## 4. File code quan trọng (phiên 12/08)

### Backend (đã sửa)
```
apps/api/app/modules/payroll/period_eligibility.py   ← MỚI
apps/api/app/modules/payroll/service.py              ← bỏ seed TOXIC; purge nháp
apps/api/app/modules/payroll/export_salary_table.py
apps/api/app/modules/attendance/ot_split.py
apps/api/app/modules/attendance/timesheet_details.py
apps/api/tests/test_payroll_resign_rehire.py
apps/api/tests/test_payroll_period_eligibility.py
apps/api/tests/test_payroll_benchmark_1519.py
```

### Frontend (đã sửa)
```
apps/web/src/shared/formatDate.ts          ← currentPayPeriod()
apps/web/src/modules/payroll/PayrollPage.tsx
apps/web/src/shared/FullscreenToggle.tsx   ← thử nghiệm
apps/web/src/modules/hr/EmployeeProfileSheet.tsx
apps/web/src/modules/timekeeping/TimekeepingPage.tsx
```

### Frontend (cần sửa — UI audit)
```
apps/web/src/shared/AiFab.tsx
apps/web/src/modules/hr/EmployeesPage.tsx
apps/web/src/modules/hr/EmployeeProfileFields.tsx
apps/web/src/styles/global.css             ← .hr-toolbar, .tk-toolbar, .payroll-toolbar-*
```

---

## 5. Môi trường chạy

```powershell
cd D:\dj-hrm\dj-hrm
docker compose ps
# Web: http://localhost:5173
# API: http://localhost:8000/health

# Test
cd apps\api && python -m pytest tests/ -q
cd apps\web && npm run test -- --run

# Restart sau sửa API
docker compose restart api
```

**Đăng nhập test:** `hr.demo` / `HrDemo@123456` (README)  
**Admin:** theo `ADMIN_PASSWORD` trong `.env` (không commit)

---

## 6. Dữ liệu / side effect phiên audit UI

| MSNV | Thay đổi | Ghi chú |
|------|----------|---------|
| 1519 | `phone = 0901234567` | Lưu thử khi test UI — revert nếu cần |

**Employee UUID 1519:** `67f87371-a211-426e-8b40-ba9876f92d74`  
URL hồ sơ: `/m/hr/employees/67f87371-a211-426e-8b40-ba9876f92d74`

---

## 7. Quyết định chờ Chủ / KTS

| # | Câu hỏi |
|---|---------|
| 1 | **Commit** toàn bộ working tree? Message / nhánh? |
| 2 | Giữ hay gỡ **Toàn màn hình** (`FullscreenToggle` — 4 file web)? |
| 3 | Phiên tiếp: **UI P0 trước** hay **UAT lương DB trước**? |
| 4 | FAB AI: cố định góc vs vẫn cho kéo? |

---

## 8. Prompt gợi ý cho phiên chat mới

Copy vào chat mới:

```
Đọc HIEN_PHAP/BAN_GIAO_PHIEN_20260812.md và làm tiếp theo mục 3 (ưu tiên do Chủ chọn).
Backend 346 pass đã xong; UI audit trong BAO_CAO_UI_UX_20260812_PM.md chưa code.
Không commit trừ khi tôi yêu cầu.
```

---

*Cập nhật: 2026-08-12 buổi tối · Thay thế mọi tóm tắt chat cho phiên này.*
