# 01 — Chấm công

Sai thì sửa file này. Ngày chốt gốc: 2026-08-10 · ngày công phiếu lương: 2026-08-17.

## Vân tay

| Luật | Giá trị đang chạy |
|------|-------------------|
| Số lần chấm / ngày | **2** — vào và ra. Không chấm giờ trưa |
| Vào / ra | **Lần bấm đầu tiên trong ngày = vào. Lần bấm cuối cùng = ra. Bỏ hết lần ở giữa** (kể cả bấm nhầm giờ trưa) |
| Bấm trùng | Nếu **cả ngày** chỉ một chuỗi chạm máy, mỗi lần **≤ 60 giây** so với lần trước (07:54 / 07:55 / 07:56) → chỉ giữ **lần đầu**, không lấy lần cuối chuỗi làm giờ ra |
| Dung sai đi trễ | **0 giây** — trễ 1 giây = đi trễ |
| Dung sai về sớm | **0 giây** — sớm 1 giây = về sớm (trừ khi có chế độ về sớm — file 07) |
| Ca đêm / ca 1-2-3 | **Không có** |
| Nguồn xưởng | Máy vân tay → Mitapro máy nhà máy → Agent đẩy VPS |
| Nguồn điện thoại | Thẳng VPS, không ghi SQL máy nhà máy |

Thiếu bấm vào hoặc ra: hệ thống **ghi nhận mốc có**, **không tự bịa** mốc còn lại, **không tính giờ công / trễ / sớm / OT** ngày đó (chưa phạt chuyên cần). AI cảnh báo HR. HR gọi NV lập biên bản (quên bấm / về sớm / đi trễ). Chế độ thai sản **không** che thiếu punch.

Sau biên bản, HR **chấm tay đủ vào và ra**. Hệ thống **tự tính** trễ/sớm từ hai mốc đó (dung sai 0 giây) và **ghi nhận số lần** để phạt chuyên cần — file 04: trễ ≥ 2 **hoặc** sớm ≥ 2 → còn 50%; trễ ≥ 5 **hoặc** sớm ≥ 5 **hoặc** có ngày vắng → 0%. Trễ và sớm đếm riêng. Quên bấm nhưng HR điền đúng giờ ca (08:00–17:00) → không phát sinh lần trễ/sớm.

## Giờ công

Ca mặc định **08:00–17:00**, trừ **1 giờ** nghỉ trưa 12:00–13:00 → đủ = **8 giờ = 1 công**.

Ra sau giờ hết ca: phần trong ca = công, phần sau = OT (file 02). Không cộng thành công > 1.

Vào trước giờ ca (ví dụ 7:52): **kẹp giờ vào ca** khi tính giờ công, không tính OT sáng (trừ Cooker — file 02).

**Lần đầu tiên = vào, lần cuối cùng = ra, bỏ hết ở giữa.** Không cắt theo 12:00. Xin về 08:30 / 08:55 / 09:10 đều nhận giờ ra, tính công từ 08:00 (kẹp) đến giờ ra; trừ trưa chỉ khi đoạn chồng 12:00–13:00.

Ngoại lệ: 07:54 rồi 07:55 rồi 07:56 là **một chuỗi bấm trùng lúc vào** → chỉ **07:54**, chưa có giờ ra. Không lấy 07:56 làm ra.

12:00 là giờ bắt đầu nghỉ trưa lúc *đếm giờ công*, không phải ngưỡng «trước giờ này mọi bấm đều là vào».

HR sửa tay đủ vào và ra: cùng quy tắc (giữ cả hai mốc, tính đoạn trong ca, **tự ghi trễ/sớm**). Thiếu một mốc: không bịa giờ, chỉ ghi nhận + cảnh báo, chưa đếm phạt chuyên cần.

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
| Vào 07:44 ra 08:30 | 0,5 | 0,0625 — xin về buổi sáng, kẹp vào 08:00 |
| Vào 07:44 ra 09:10 | 1,1667 | 0,1458 — kẹp vào 08:00, không trừ trưa, về sớm so với 17:00 |
| Vào 8:15 ra 17:00 | 7,75 | 0,9688 **và** 1 lần đi trễ |

Thai sản / nuôi con về đúng giờ được phép, bù đủ 8h → **1,0 ngày** (file 07).
