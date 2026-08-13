# Báo cáo bug + test fail — gửi Kiến trúc sư trưởng DJ-HRM

> **Phiên:** 2026-08-12 (buổi tối)  
> **Người lập:** Cursor AI (theo chỉ đạo Chủ phần mềm)  
> **Đối tượng:** Kiến trúc sư trưởng phát triển phần mềm DJ-HRM  
> **Mẫu:** `20_HIEN_PHAP_V2_QUY_TRINH.md` §20.6 + `08_MODULE_API_HOP_DONG.md`  
> **Trạng thái code:** đã sửa trên working tree · **chưa commit** (chờ Chủ duyệt)

---

## 0. Tóm tắt điều hành

| Chỉ số | Trước phiên | Sau phiên |
|--------|-------------|-----------|
| API pytest | **339 pass / 7 fail** | **346 pass / 0 fail** |
| Web vitest | 19 pass | 19 pass |
| Bug nghiệp vụ P0 | 2 (lương + phụ cấp) | **0** (đã sửa) |
| Docker API | — | `docker compose restart api` ×2 |

**Kết luận kiến trúc:** Các lỗi chính do **logic nghiệp vụ thiếu lọc trạng thái NV** và **fixture test/seed lẫn vào luồng production**. Test fail còn lại chủ yếu do **test cũ chưa đồng bộ Hiến pháp `ot_split`** (grace 17:15, OT trên sổ T3/T5) — không phải regression engine.

---

## 1. Bug nghiệp vụ đã sửa (P0)

### 1.1 NV đã nghỉ vẫn còn trên bảng Tính lương (MSNV 1604, 1718)

**Triệu chứng:** Tái tuyển → nghỉ lại → tab Nhân sự đã «Đã nghỉ» nhưng **Tính lương** vẫn hiện tên, đôi khi **âm tiền** (0 công, vẫn trừ BH/phí).

**Nguyên nhân gốc:**
- `calculate_period` duyệt mọi `timesheet_month` chỉ lọc `deleted_at`, **không** kiểm tra `resign_date` / trạng thái nghỉ trước kỳ.
- Phiếu lương nháp cũ **không bị xóa** khi NV không còn thuộc kỳ.

**Sửa (module `payroll`):**
- Thêm `period_eligibility.py` → `employee_on_payroll_period()` (cùng tinh thần `_was_on_payroll` ở báo cáo KPI).
- Tính lương: bỏ qua NV không thuộc kỳ; `_purge_ineligible_draft_payslips()` trước/sau calculate.
- Lọc danh sách phiếu, xuất Excel, mô phỏng, OT ngoài.

**Test:** `tests/test_payroll_resign_rehire.py`, `tests/test_payroll_period_eligibility.py`.

**Nghiệm thu trên DB thật:** Mở kỳ → **Tính lương lại**. NV nghỉ **trước** tháng đang xem phải biến mất khỏi lưới.

---

### 1.2 Xóa phụ cấp TOXIC trên hồ sơ nhưng Tính lương vẫn có (MSNV 1519)

**Triệu chứng:** Thêm phụ cấp độc hại → xóa trên hồ sơ → Lưu → Tính lương vẫn còn TOXIC.

**Nguyên nhân gốc:** Mỗi lần `calculate_period` gọi `seed_fixture_allowance_assignments()` — hàm **chỉ dành fixture test** — tự gán lại TOXIC cho NV xưởng (`direct`) nếu assignment đã bị xóa.

**Sửa:** Gỡ `seed_fixture_allowance_assignments` khỏi `service.calculate_period`. Fixture vẫn chạy trong `conftest.py` (pytest).

**Test:** `tests/test_payroll_benchmark_1519.py::test_msnv_1519_deleted_toxic_not_reseeded_on_calculate`.

---

## 2. Cải tiến UX / API (P2 — không phải bug)

| Hạng mục | Mô tả |
|----------|--------|
| Kỳ mặc định | Portal dùng `currentPayPeriod()` — không còn kẹt `2025-10` |
| Xuất bảng lương | Chọn **bộ phận** / **1 MSNV** (API đã có, UI mới bổ sung) |
| Toàn màn hình | Nút thử `⛶ Toàn màn` góc phải Portal staff (có thể revert bằng git checkout 4 file web) |

---

## 3. Bảng 7 test fail → đã sửa (chấm công / Hiến pháp `ot_split`)

Quy tắc Hiến pháp (code `ot_split.py`): **chỉ tính OT khi bấm ra sau 17:15**; số phút OT tính từ **17:00**; **T3/T5** → OT trên sổ, ngày khác → OT ngoài (`OT_EXT`).

| # | Test | Nguyên nhân fail | Cách xử lý | Pass |
|---|------|------------------|------------|------|
| 1 | `test_attendance_days::test_push_auto_builds_attendance_day` | Kỳ vọng OT 5p lúc 17:05 | Cập nhật kỳ vọng: `ot_minutes=0` | ✅ |
| 2 | `test_attendance_days_extend_34::test_apply_calc_weekday_ot_night_zero` | Thiếu field `ot_on_books_minutes` / `ot_external_minutes` trên `DayCalcResult` | Bổ sung field fixture | ✅ |
| 3 | `test_attendance_days_extend_34::test_apply_calc_sunday_hours` | Giống #2 | Bổ sung field fixture | ✅ |
| 4 | `test_attendance_punch_dedupe_32::test_five_taps_within_60s_become_one_check_in` | Kỳ vọng `first_in=None` sau 5 lần bấm 07:50 | Sửa kỳ vọng: **một giờ vào** `first_in=07:50` (đúng engine + 24§) | ✅ |
| 5 | `test_timesheet::test_rebuild_timesheet_from_punches` | Kỳ vọng `ot_hours_weekday=0.08` từ 17:05 | `ot_hours_weekday=0.0` | ✅ |
| 6 | `test_timesheet_month_details_35::test_rebuild_creates_wt_and_ot_details` | Ngày T4 + 17:05 không sinh detail OT | Đổi **14/10 (T3)** + ra **17:20** → 0.33h OT trên sổ | ✅ |
| 7 | `test_timesheet_month_details_35::test_aggregate_unit` | Fixture thiếu `worked_hours`, `ot_on_books_minutes`; code không chịu `None` | Sửa test + `(d.ot_on_books_minutes or 0)` trong `timesheet_details.py` | ✅ |

**Lệnh xác nhận:** `python -m pytest tests/ -q` → **346 passed**.

---

## 4. Ánh xạ file code đã đụng

### Backend (bug + test liên quan)

| File | Thay đổi |
|------|----------|
| `apps/api/app/modules/payroll/period_eligibility.py` | **Mới** — lọc NV thuộc kỳ lương |
| `apps/api/app/modules/payroll/service.py` | Bỏ seed TOXIC; lọc + purge phiếu nháp |
| `apps/api/app/modules/payroll/export_salary_table.py` | Lọc export theo eligibility + MSNV/BP |
| `apps/api/app/modules/payroll/simulate.py` | Lọc mô phỏng |
| `apps/api/app/modules/payroll/ot_external.py` | Lọc OT ngoài |
| `apps/api/app/modules/payroll/router.py` | Query `employee_code` export |
| `apps/api/app/modules/attendance/timesheet_details.py` | Null-safe OT split columns |
| `apps/api/tests/test_payroll_resign_rehire.py` | **Mới** |
| `apps/api/tests/test_payroll_period_eligibility.py` | **Mới** |
| `apps/api/tests/test_attendance_*.py`, `test_timesheet*.py` | Đồng bộ Hiến pháp |

### Frontend

| File | Thay đổi |
|------|----------|
| `apps/web/src/shared/formatDate.ts` | `currentPayPeriod()` |
| `apps/web/src/modules/payroll/PayrollPage.tsx` | Kỳ mặc định + lọc xuất |
| `apps/web/src/shared/FullscreenToggle.tsx` | Thử nghiệm toàn màn hình |
| Các trang Overview/Report/Insurance/Timekeeping | Kỳ mặc định |

---

## 5. Nghiệm thu theo file 13 (test)

| Tiêu chí | Kết quả |
|----------|---------|
| Regression pytest toàn bộ | **346/346 pass** |
| Luồng tái tuyển → nghỉ → kỳ sau | Test tự động pass |
| TOXIC không tự gán lại khi tính lương | Test 1519 pass |
| OT grace 17:15 | Test engine + API days đồng bộ |
| Idempotent Decimal lương | Không đổi trong phiên này |

---

## 6. Lệch so với thiết kế

| Mục | Ghi chú |
|-----|---------|
| `ot_split` trong file 22/04 | Quy tắc đã code trong `ot_split.py` + policy seed; **nên bổ sung § vào `22_QUY_TAC_NGHIEP_VU.md`** để test và HR cùng một nguồn |
| Fullscreen Portal | Thử nghiệm UI — chưa ghi trong `23_UI_MAN_HINH.md` |

---

## 7. Chặn / cần Chủ quyết

| # | Việc | Đề xuất |
|---|------|---------|
| 1 | **Commit** các thay đổi phiên 12/08 | Chủ quyết message + nhánh |
| 2 | Giữ hay gỡ nút **Toàn màn hình** | Giữ nếu HR thích; gỡ = checkout 4 file web |
| 3 | NV nghỉ **trong tháng** vẫn trên bảng lương | **Đúng nghiệp vụ** — chốt lương đến ngày nghỉ; cần HR nhập đúng `resign_date` |
| 4 | Ghi `ot_split` vào Hiến pháp 22 | Kiến trúc sư duyệt 1 đoạn → AI cập nhật file |

---

## 8. Việc tiếp theo (đề xuất kiến trúc)

1. **Nghiệm thu tay** trên DB công ty: MSNV 1604, 1718, 1519 — Tính lương kỳ mở.
2. **Commit** gói: `payroll eligibility + TOXIC seed fix + ot_split test sync`.
3. Bổ sung **`22_QUY_TAC_NGHIEP_VU.md` § OT split** (17:15, T3/T5, OT_EXT).
4. HR đào tạo ngắn: xuất lương theo BP/1 người; nghỉ việc phải có ngày nghỉ trước khi tính kỳ mới.

---

## 9. Phụ lục — lệnh kiểm tra nhanh

```powershell
cd D:\dj-hrm\dj-hrm\apps\api
python -m pytest tests/ -q

cd D:\dj-hrm\dj-hrm\apps\web
npm run test -- --run
```

```powershell
cd D:\dj-hrm\dj-hrm
docker compose restart api
```

---

*Báo cáo này thay thế trạng thái «7 fail» trong chat — là nguồn chính thức cho phiên 2026-08-12 trong `HIEN_PHAP/`.*
