# 05 — Nghỉ và phép năm

Sai thì sửa file này.

## Mười bốn loại nghỉ

Cột **% trả** = công ty trả lương ngày nghỉ. 0% = BHXH hoặc không lương.

| Mã | Tên | % công ty trả | Ghi chú |
|----|-----|---------------|---------|
| ALE | Phép năm | 100 | Miễn trừ lần trễ/sớm (nửa buổi) |
| FLE | Tang | 100 | Miễn trừ như trên |
| WED | Cưới | 100 | Miễn trừ như trên |
| LA | Tai nạn LĐ | 100 | |
| OFF | Nghỉ bù | 100 | Không tính vắng |
| TMP | Hết hàng | **70** | Không tính vắng; **không** vào tử số phụ cấp |
| PT | Khám thai | 0 | BHXH · mất chuyên cần (trừ khi HR gán mã miễn khác) |
| MLE | Thai sản (nghỉ đẻ) | 0 | BHXH |
| MC | Sẩy thai | 0 | BHXH |
| SLE | Ốm | 0 | BHXH |
| SCH | Con ốm | 0 | BHXH |
| NOP | Không phép | 0 | **Vắng** → mất chuyên cần |
| NON | Không chấm | 0 | **Vắng** |
| PER | Có phép | **HR phải khai %** | Không được đoán |

```
tiền ngày nghỉ = (lương HĐ) / divisor × số ngày × (% trả / 100)
```

Mỗi loại nghỉ là **một dòng** trên phiếu, không gộp vào lương ngày công.

Ca / về sớm thai sản: file 07 — không phải mã nghỉ này.

## Phép năm

| Luật | Giá trị đang chạy |
|------|-------------------|
| Mốc người mới | **14** ngày / năm |
| Thâm niên | **+1 ngày** mỗi đủ **5 năm** theo ngày vào |
| Tích lũy | `round(số tháng × mốc năm / 12, 2)` |
| Người cũ | Tích từ 01/01 |
| Người mới | Tích từ ngày vào |
| Sổ | Bút toán (được cấp / đã dùng / còn lại) — không tính lại từ đầu mỗi lần mở danh sách |

Nghỉ thai sản / không lương **không** dừng tích phép.

### Trả tiền phép còn khi nghỉ việc

```
tiền = lương HĐ / 26 × số ngày phép chưa dùng
```

Mẫu số chỗ này **luôn 26**, không dùng divisor tháng.
