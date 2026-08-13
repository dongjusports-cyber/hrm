# Báo cáo audit — Tab TÍNH LƯƠNG

> **Ngày:** 2026-08-13 · **Phạm vi:** Module `/m/payroll` + engine + phiếu lương  
> **Phương pháp:** pytest API + rà code UI + neo MSNV 1519

---

## 1. Tóm tắt

| Hạng mục | Kết quả |
|----------|---------|
| API tests payroll | **19/19 pass** |
| Benchmark MSNV 1519 (07/2026) | **Pass** — net 9.682.398 |
| Báo cáo này | **Hoàn thành** (audit lần 1) |
| Sẵn sàng pilot tính lương | **Có** — với **2 lỗi P1 UI** |

---

## 2. Phạm vi đã kiểm

| Tab UI | Component | Ghi chú |
|--------|-----------|---------|
| Bảng lương | `PayrollGridSection` | 5 chế độ xem cột |
| Phiếu lương | `PayrollPayslipSection` | 3 khối ngang |
| Chạy thử | `PayrollSimulateSection` | Không ghi DB |
| Điều chỉnh | modal trong `PayrollPage` | Truy lĩnh / khấu trừ |
| Xuất ATM/CASH | API export | Lọc bộ phận / MSNV |

---

## 3. API — kết quả test

```
test_payroll_calculate, benchmark_1519, publish_lock,
export, simulate_410, ui_49, resign_rehire, period_eligibility
→ 19 passed
```

**Neo UAT:** `test_msnv_1519_july_2026_matches_genussuite` — khớp GenusSuite.

---

## 4. Lỗi / thiếu sót

### P1 — UI logic (nên sửa trước kỳ lương thật)

| ID | Vấn đề | File |
|----|--------|------|
| L1 | Nút **Phát hành** vẫn enabled khi kỳ `published` | `PayrollPage.tsx` — `canPublish = periodStatus !== "locked"` (thiếu loại trừ `published`) |
| L2 | Lưu điều chỉnh lương **không validate** số tiền / MSNV trước submit | `PayrollPage` adj form |

### P2 — Tự động hóa (đề xuất, chưa làm)

| ID | Đề xuất |
|----|---------|
| L3 | **Chỉ** tự động bước **Tính lương** (async + pre-flight); **không** auto publish/lock |
| L4 | Gate: kỳ mở, công đã sync, không còn ca lỗi P0 |

### Đã đúng / không phải bug

- MSNV **1604/1718** resigned: chỉ loại khỏi lương khi `status=resigned`; tái tuyển test → vào lại bảng lương — **đúng**.
- Engine decimal, snapshot policy — **ổn**.

---

## 5. UI/UX (§23)

| Quy ước | Đạt? |
|---------|------|
| Ghim MSNV + Họ tên; Thực lãnh phải | ✅ |
| 5 chế độ xem cột | ✅ |
| Cột tiền canh phải, tabular-nums | ✅ |
| Kỳ mặc định tháng hiện tại | ✅ |

---

## 6. Kết luận

**Báo cáo tab Tính lương: XONG (audit).**  
Engine **tin cậy** (19/19 + benchmark 1519). Sửa **L1** trước kỳ pilot để tránh phát hành nhầm lần 2.

---

*Liên quan: `03_CONG_THUC_LUONG.md`, `22_QUY_TAC_NGHIEP_VU.md`*
