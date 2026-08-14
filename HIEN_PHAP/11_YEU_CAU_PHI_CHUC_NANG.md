# 11 — Yêu cầu phi chức năng (vừa đủ cho 500 người)

> Nguyên tắc P11: cân xứng quy mô. Không tối ưu thừa.

## 11.1 Hiệu năng mục tiêu (đủ dùng, không hơn)

| Hạng mục | Mục tiêu |
|----------|----------|
| Trang thường (list, form) | < 2 giây |
| Bảng lương AG-Grid ~500 dòng | < 3 giây |
| Tính lương toàn nhà máy (~500 NV) | < 2 phút (chạy nền, có progress) |
| Đồng bộ Mitapro 1 ngày | < 1 phút |
| Người dùng đồng thời | ~20–30 (HR/KT) + ~500 worker xem rải rác |

→ Không cần thiết kế cho “10.000 user”. Nếu sau này mở rộng, xử lý khi tới.

## 11.2 Tính sẵn sàng

| Hạng mục | Mức |
|----------|-----|
| Uptime mục tiêu | ~99% (giờ hành chính quan trọng) |
| Bảo trì | Ngoài giờ, báo trước |
| Không cần | Multi-region, auto-failover, HA cluster (thừa cho quy mô này) |

## 11.3 Tài nguyên

- Local test: Win10 i3 16GB — Docker phải chạy nhẹ (Postgres + Redis + api + web).
- VPS: 4 vCPU / 8GB đủ. Theo dõi RAM Postgres.

## 11.4 Timeout & giới hạn

| Hạng mục | Giá trị seed |
|----------|--------------|
| API request timeout | 30s (job dài → chạy nền, trả job_id) |
| Job tính lương | chạy queue, không block HTTP |
| Upload Excel | ≤ 10MB |
| JWT access | 8 giờ; refresh 7 ngày |

## 11.5 Quy tắc làm nền (async) — chỉ khi cần

Chạy nền: tính lương, đồng bộ Mitapro, gọi Gemini, export lớn.  
Còn lại: xử lý đồng bộ cho đơn giản. **Không** dựng pipeline sự kiện phức tạp.



---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
*Tiếp: `12_BAO_MAT_BACKUP_VAN_HANH.md`*
