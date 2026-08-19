# 03 — Lương ngày, kỳ, mẫu số, thử việc

Sai thì sửa file này.

## Kỳ và chi trả

| Hạng mục | Luật |
|----------|------|
| Kỳ tính công / lương | Ngày **01 → cuối tháng** |
| Ngày trả lương | Ngày **08** tháng sau (trùng nghỉ: Admin lệch 1 ngày) |
| Tiền | VND, làm tròn **đồng** ở bước cuối (nửa lên). Giờ/ngày giữ số lẻ đến lúc đó |

## Mẫu số tháng (`divisor`)

Đếm ngày làm việc theo lịch công ty (T2–T7 trừ lễ). Trần **26**.

```
divisor = số ngày làm việc theo lịch
nếu divisor > 26 thì divisor = 26
```

| Tháng | Ngày lịch | Mẫu số |
|-------|-----------|--------|
| 27 ngày công | 27 | **26** |
| 26 ngày công | 26 | 26 |
| Tết còn 20 ngày | 20 | **20** |

Mẫu số này dùng cho lương ngày, OT, phụ cấp chia theo ngày. **Trả phép khi nghỉ việc** dùng **26 cố định** (file 05).

## Lương ngày công

```
Chính thức: lương HĐ / divisor × số ngày công chính thức
Thử việc:   lương thử việc / divisor × số ngày công thử việc
```

Ngày công giữ số lẻ từ phút chấm (không cắt 4 chữ số kiểu phần mềm cũ).

Nghỉ chế độ (REM / ốm BHXH…) **công ty không trả** lương ngày — trừ khi HR gán loại nghỉ có % trả (file 05).

## Thử việc

| Luật | Giá trị đang chạy |
|------|-------------------|
| Lương thử việc | **85%** lương HĐ |
| Mốc hết thử việc | **Ngày ký HĐ chính thức** |
| Phụ cấp lúc thử việc | **0** (chuyên cần, đi lại, chức vụ, tay nghề, độc hại, thâm niên, khác) |
| Vắng lúc thử việc | **Không** tính vào mất chuyên cần |

Một người vào giữa tháng có **hai đoạn**: thử việc + chính thức trên cùng kỳ.
