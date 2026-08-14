# Báo cáo audit — Tab CHẤM CÔNG

> **Ngày:** 2026-08-13 · **Phạm vi:** Module `/m/timekeeping` + engine công + sync  
> **Phương pháp:** pytest API + rà code UI + tham chiếu báo cáo performance

---

## 1. Tóm tắt

| Hạng mục | Kết quả |
|----------|---------|
| API tests (engine + ngày + punch) | **50/51 pass** (1 fail `test_holiday_ot`) |
| UI chính | `TimekeepingPage` — Công ngày + Tổng hợp tháng + sync sheet |
| Báo cáo này | **Hoàn thành** (audit lần 1) |
| Performance chi tiết | Xem `BAO_CAO_PERFORMANCE_20260813.md` |

---

## 2. Phạm vi đã kiểm

| Màn | File | Ghi chú |
|-----|------|---------|
| Bảng công ngày | `DailyGridPanel.tsx` | Load ~350 dòng/ngày; sửa F2 |
| Tổng hợp tháng | `TimekeepingPage` view monthly | AG-Grid |
| Đồng bộ Mitapro | `MitaproSyncPanel.tsx` | Full-screen sheet |
| OT ngoài | `OtExternalPreviewSheet.tsx` | Xuất Excel ATM riêng |
| Engine tính công | `attendance/engine*.py` | OT grace 17:15, dedupe punch |

---

## 3. API — kết quả test

```
test_attendance_engine, review, punches_31, punch_dedupe_32,
penalty_44, days_extend_34, days, day_grid_37, day_calc_33
→ 50 passed, 1 failed
```

**Fail:** `test_attendance_engine.py::test_holiday_ot` — cần điều tra OT ngày lễ (không chặn pilot nếu kỳ UAT không dùng lễ).

---

## 4. Lỗi / rủi ro (ưu tiên)

### P0 — Performance & vận hành (từ báo cáo performance)

| ID | Vấn đề |
|----|--------|
| C1 | Agent poll 15 phút — chậm phản hồi sync |
| C2 | Ingest từng punch + recalc inline — tải DB cao |
| C3 | Sau sửa ô lưới ngày: **reload full grid** — UX chậm |
| C4 | Search lưới ngày **không debounce** |

### P1 — Nghiệp vụ / UI

| ID | Vấn đề |
|----|--------|
| C5 | `TimeInput24` + ESC: đã xử lý riêng; đồng bộ với quy tắc PR #7 |
| C6 | Chi tiết NV ngày công: FullScreenSheet — ESC không đóng (PR #7) |

### P2

- Tab phụ đã gom (U6 Done §23.11)  
- Toolbar ≤46px @1366 (U4 Done)  

---

## 5. UI/UX

| Quy ước §23 | Đạt? |
|-------------|------|
| Một vùng cuộn dữ liệu | ✅ |
| Toolbar không wrap @1366 | ✅ |
| Sửa tại chỗ / dán Excel | ✅ (daily grid) |
| Chip "Chỉ cần xử lý" | ⚠️ Kiểm tra tay trên dữ liệu thật |

---

## 6. Kết luận

**Báo cáo tab Chấm công: XONG (audit).**  
Engine **ổn** (50/51 test). Pilot chấm công **được** nếu chấp nhận tốc độ sync/grid (P0 performance) và fix `test_holiday_ot` khi có kỳ có ngày lễ.

---

*Liên quan: `BAO_CAO_PERFORMANCE_20260813.md` (P0 sync/grid chi tiết)*
