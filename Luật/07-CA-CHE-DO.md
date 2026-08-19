# 07 — Ca làm việc và chế độ về sớm

Sai thì sửa file này.

## Ba ca

Engine tính **theo ca của Tổ**, không một lịch chung cho cả nhà máy. HR đổi ca trên hồ sơ / tổ.

| Mã ca | Tổ | Vào | Hết ca (mốc về sớm) | Nghỉ trưa | Bắt đầu OT |
|-------|-----|-----|---------------------|-----------|------------|
| ADMIN | Mặc định | 08:00 | **17:00** | 12:00–13:00 | 17:00 (vẫn cần cổng 17:30 — file 02) |
| CLEANER | Tạp vụ, code **02** | 07:00 | **16:00** | 12:00–13:00 | **17:00** (16:00–17:00 = nghỉ, không OT) |
| COOKER | Nấu ăn, code **05** (1581 / 1733) | 08:00 | **17:00** | 12:00–13:00 | Chiều như ADMIN + OT sáng nếu bấm **trước 6:00** |

Tạp vụ ra **16:00 = đúng giờ**, không về sớm. Có bấm 16:xx **không** thành OT.

Hết ca và mốc OT **tách nhau** — không suy OT từ giờ về.

## Chế độ về sớm (thai sản / nuôi con)

HR khai tay trên hồ sơ. Máy **không** tự suy từ giới tính hay tuổi con.

| Trường | Luật |
|--------|------|
| Loại | Đang mang thai (`PREGNANT`) · Nghỉ đẻ (`MATERNITY`) · Nuôi con (`CHILD`) |
| Giờ về sớm | 1 / 2 / 3 (gợi ý: thai 1h, nuôi 2h). Nghỉ đẻ = 0h, gắn mã MLE |
| Từ ngày – Đến ngày | Bắt buộc. **Không tính lùi** trước ngày gán |
| Chấm dứt | HR bấm chấm dứt → đến ngày = hôm nay |
| Nhắc | 3 ngày trước ngày hết |

Chỉ khi **có đủ giờ vào và giờ ra**.

```
giờ được về = hết ca (theo tổ) − số giờ chế độ
Ra đúng hoặc sau mốc đó: không tính về sớm; giờ công = min(giờ thực + giờ chế độ, 8)
Ra trước mốc: phần thiếu = về sớm; vẫn cộng giờ chế độ, không quá 8h
```

Ví dụ ca 08–17, thai sản 1h → được về 16:00:

| Giờ ra | Giờ thực | Giờ công | Về sớm |
|--------|----------|----------|--------|
| 16:00 | 7h | **8h** | 0 |
| 15:00 | 6h | **7h** | 60 phút (1 lần) |
| 17:00 | 8h | **8h** (không thành 9h) | 0 |

**Phụ cấp tiền Con nhỏ** ≠ chế độ giờ Nuôi con. Có thể có một, cả hai, hoặc không.
