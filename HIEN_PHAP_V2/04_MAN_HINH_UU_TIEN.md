# 04 — Màn hình ưu tiên UI V2

> Thứ tự làm để HR thấy giá trị sớm nhất sau merge. AG-Grid **giữ** — chỉ đổi chrome xung quanh.

---

## P1 — Làm trước (HR dùng hàng ngày)

| # | Màn | Route gợi ý | Ghi chú |
|---|-----|-------------|---------|
| 1 | **Portal 8 ô** | `/` | Khay module, Ctrl+K |
| 2 | **Danh sách NV** | `/m/hr/lists/*` | Toolbar gọn 1366; AG-Grid |
| 3 | **Hồ sơ NV overlay** | FullScreenSheet | 5 cột; phụ cấp add/xóa |
| 4 | **Bảng lương kỳ** | `/m/payroll` | Cột tiền; export Excel |

---

## P2 — Làm sau P1

| # | Màn | Ghi chú |
|---|-----|---------|
| 5 | **Chấm công** — Tổng hợp + Bảng ngày | Tab full-width |
| 6 | **Chấm công** — Đồng bộ Mitapro | Nút «Đồng bộ ngay» |
| 7 | **Tăng lương** | `/m/hr/salary-raise` |
| 8 | **Duyệt phép / Rà soát** | Tab phụ chấm công |

---

## P3 — Cuối

| # | Màn |
|---|-----|
| 9 | Admin Cấu hình (chỉ admin) |
| 10 | Worker Portal `/worker` (mobile PWA) |
| 11 | Audit, KPI, Báo cáo |

---

## Tiêu chí «xong» từng màn V2

- [ ] Login + logout OK
- [ ] API giống bản 5173 (cùng JSON)
- [ ] 1366×768 không wrap toolbar che lưới
- [ ] 1920×1080 grid cuộn trong vùng dữ liệu
- [ ] Lưu hồ sơ không nhảy trang
- [ ] Vitest smoke (nếu có component mới)

---

## Không làm trong V2 phase 1

- Đổi luồng nghiệp vụ (thêm bước duyệt mới)
- TNCN phase 2
- Đa ngôn ngữ EN

---

*Tiếp: `05_CHECKLIST_MERGE_SAU_V1.md`*
