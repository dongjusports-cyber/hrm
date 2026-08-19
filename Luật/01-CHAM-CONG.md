# 01 — Chấm công

Sai thì sửa file này. Ngày chốt gốc: 2026-08-10 · ngày công phiếu lương: 2026-08-17.

## Vân tay

| Luật | Giá trị đang chạy |
|------|-------------------|
| Số lần chấm / ngày | **2** — vào và ra. Không chấm giờ trưa |
| Gom chấm liên tục | Trong **60 giây** = 1 lần. Giữ **sớm nhất** = vào, **muộn nhất** = ra |
| Dung sai đi trễ | **0 giây** — trễ 1 giây = đi trễ |
| Dung sai về sớm | **0 giây** — sớm 1 giây = về sớm (trừ khi có chế độ về sớm — file 07) |
| Ca đêm / ca 1-2-3 | **Không có** |
| Nguồn xưởng | Máy vân tay → Mitapro máy nhà máy → Agent đẩy VPS |
| Nguồn điện thoại | Thẳng VPS, không ghi SQL máy nhà máy |

Thiếu bấm vào hoặc ra: HR xử lý tay trên lưới ngày. Chế độ thai sản **không** che thiếu punch.

## Giờ công

Ca mặc định **08:00–17:00**, trừ **1 giờ** nghỉ trưa 12:00–13:00 → đủ = **8 giờ = 1 công**.

Ra sau giờ hết ca: phần trong ca = công, phần sau = OT (file 02). Không cộng thành công > 1.

Vào trước giờ ca (ví dụ 7:52): **kẹp giờ vào ca**, không tính OT sáng (trừ Cooker — file 02).

## Ngày công trên phiếu lương

Lưới chấm công hiện **giờ**. Phiếu lương dùng ngày:

```
ngày công một ngày = giờ công / 8
ngày công tháng    = tổng các ngày, hiện 2 số (làm tròn xuống)
```

| Tình huống | Giờ công | Ngày công |
|------------|----------|-----------|
| Đủ 08:00–17:00 | 8,00 | 1,0 |
| Chỉ chiều 13:00–17:00 | 4,00 | 0,5 |
| Về sớm 08:00–11:25 | 3,42 | 0,4275 — tháng cộng dồn rồi hiện 2 số |
| Vào 8:15 ra 17:00 | 7,75 | 0,9688 **và** 1 lần đi trễ |

Thai sản / nuôi con về đúng giờ được phép, bù đủ 8h → **1,0 ngày** (file 07).
