# 06 — Bảo hiểm, công đoàn, thuế

Sai thì sửa file này.

## Nền đóng BHXH (khác nền OT — file 04)

```
nền = lương HĐ + chức vụ + tay nghề + độc hại + thâm niên + PCCC + HSE
nếu nền ≥ 46.800.000 thì lấy 46.800.000
```

**Không** gồm chuyên cần, đi lại, đào tạo, phụ cấp khác.

Kiểm chứng 1519 kỳ 07/2026: lương ngày 8.335.000 + thâm niên 550.000 = nền **8.885.000**.

## Tỷ lệ đang chạy

| Khoản | Tỷ lệ / số |
|-------|------------|
| BHXH | 8% |
| BHYT | 1,5% |
| BHTN | 1% |
| Công đoàn | **44.100** đ cố định (HR ghi đè từng người được) |

## Tháng nào thì đóng (luật 12 ngày / ngày 16)

Phải đang tham gia BHXH trên hồ sơ.

| Tình huống | Đóng tháng đó? |
|------------|----------------|
| Nghỉ thai sản (chế độ MATERNITY) giao kỳ | **Không** (tạm dừng BH + công đoàn) |
| Thôi việc **trước ngày 16** | **Không** — dù đủ 12 công |
| Vào làm **từ ngày 16** trở đi trong tháng | Chỉ đóng nếu công ≥ **12** ngày |
| Còn tên, vào trước ngày 16 (hoặc không phải tháng vào) | **Có** — không chờ đủ 12 công giữa tháng |

## Thuế TNCN

Trên phần mềm: `pit_enabled = false` (chưa khấu trừ trên phiếu). Khi bật:

| Giảm trừ | Số |
|----------|-----|
| Bản thân | 11.000.000 đ |
| Mỗi người phụ thuộc | 4.400.000 đ |

Số người phụ thuộc lấy từ bảng thân nhân, không gõ tay trên phiếu.

Biểu lũy tiến (khi bật): 5% / 10% / 15% / 20% / 25% / 30% / 35% theo bậc nhà nước.

```
Tổng thu nhập      = lương ngày + lương nghỉ + OT trong sổ + mọi phụ cấp
Thu nhập chịu thuế = Tổng thu nhập − BH bắt buộc
Thực lãnh          = Tổng thu nhập − mọi khấu trừ (BH, công đoàn, thuế, tạm ứng, trừ khác)
```

OT **ngoài** (ATM) không vào phiếu / BHXH / thuế.

## Bài neo — MSNV 1519, kỳ 07/2026

Tính lại phải đúng từng đồng:

| Bước | Kết quả |
|------|---------|
| Đơn giá ngày 8.335.000 ÷ 26 | 320.577 |
| Lương ngày 26,0 | 8.335.000 |
| Phép năm 1 ngày | 320.577 |
| Trợ cấp 623.077 + 830.769 + 550.000 | 2.003.846 |
| **Tổng thu nhập** | **10.659.423** |
| BHXH + BHYT + BHTN + CĐ | 977.025 |
| **Thực lãnh** | **9.682.398** |
