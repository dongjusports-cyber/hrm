# 04 — Phụ cấp và chuyên cần

Sai thì sửa file này. Ngưỡng chuyên cần mới: 2026-08-15.

## Mức chuẩn (chia theo ngày rồi nhân tỷ lệ)

| Khoản | Mức tháng đang chạy |
|-------|---------------------|
| Chuyên cần | **600.000** đ |
| Đi lại | **800.000** đ |

```
số ngày hưởng = công thực tế + phép năm + tang + cưới + lễ + nghỉ bù
                (mã: WT, ALE, FLE, WED, HOL, COM)
tiền đã chia  = mức chuẩn / divisor × số ngày hưởng
```

`TMP` (hết hàng) **không** vào tử số.

Tháng 27 ngày, đi đủ 27: chuyên cần = 600.000 / 26 × 27 = **623.077** đ.

## Tỷ lệ chuyên cần (nhân sau cùng)

Đếm **trễ** và **sớm** riêng, không gộp. Trễ 1 + sớm 1 vẫn **100%**.

Nguồn đếm: ngày đã **đủ vào và ra** (máy hoặc HR chấm tay sau biên bản), `late_minutes > 0` / `early_minutes > 0`. Ngày chấm lẻ (thiếu một mốc) **không** đếm — HR chưa xác nhận.

```
100%
trễ ≥ 2 lần  HOẶC  sớm ≥ 2 lần                         → 50%
trễ ≥ 5 lần  HOẶC  sớm ≥ 5 lần  HOẶC  có ngày vắng     → 0%
```

**Không tính** một lần trễ/sớm nếu ngày đó đủ cả ba: mã nghỉ `ALE` / `FLE` / `WED` · nghỉ **dưới 8 giờ** · có chấm vào và ra.

**Ngày vắng** (mất chuyên cần): mã `NOP`, `NON` (và nghỉ 0% khác, trừ ALE/FLE/WED/TMP/OFF), và **sau hết thử việc**.

Thử việc: chuyên cần = **0** (file 03).

## Phụ cấp thâm niên (theo tháng làm việc)

| Số tháng | Tiền |
|----------|------|
| < 6 | 0 |
| 6 – 119 | `FLOOR(tháng / 6) × 25.000` |
| 120 – 191 (10–15 năm) | 550.000 |
| 192 – 251 (16–20 năm) | 600.000 |
| 252 – 371 (21–30 năm) | 650.000 |
| ≥ 372 (từ 31 năm) | 700.000 |

Tháng = `FLOOR` số tháng từ ngày vào đến cuối kỳ.

## Nền tính OT vs nền BHXH (cờ đang chạy)

| Phụ cấp | Vào nền BHXH | Vào nền OT |
|---------|:------------:|:----------:|
| Chức vụ | Có | Có |
| Độc hại | Có | Có |
| Tay nghề | Có | Có |
| Thâm niên | Có | Có |
| PCCC + HSE | Có | Không (không nằm list OT) |
| Đào tạo | Không | Có |
| **Chuyên cần** | **Không** | **Có** (mức chuẩn) |
| Đi lại | Không | Không |
| Khác / con nhỏ (tiền) | Không | Không |

Phụ cấp **tiền** «Con nhỏ» ≠ chế độ **giờ** «Nuôi con» (file 07).
