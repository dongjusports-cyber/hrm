# 22 — QUY TẮC NGHIỆP VỤ ĐÃ CHỐT

> Mọi công thức dưới đây trích từ `HIEN_PHAP/GenuSuite HRM/GenuiSuite_Logic.sql` (có ghi số dòng)
> hoặc do Chủ chốt trực tiếp. **Không suy diễn thêm.** Thấy thiếu thì đọc file `.sql`, không đoán.

---

## 22.1 CHẤM CÔNG — Chủ chốt ngày 2026-08-10

| Quy tắc | Giá trị |
|---------|---------|
| Số lần chấm mỗi ngày | **2** — vào và ra (vân tay Mitapro). **Không chấm giờ trưa** |
| Ca làm việc | **08:00 – 17:00**, một ca hành chính duy nhất |
| Nghỉ trưa | 12:00 – 13:00, **trừ 1 giờ** khi tính công |
| Ca đêm / ca 1-2-3 | **KHÔNG CÓ** — `night_shift_enabled = false` |
| Tăng ca | Sau 17:00, thường kết thúc **20:00 hoặc 21:00** |
| Dung sai đi trễ | **0 giây** — trễ 1 giây là đi trễ |
| Dung sai về sớm | **0 giây** — sớm 1 giây là về sớm |

### Quy tắc tách công và tăng ca
Ra lúc 20:00 thì **08:00–17:00 = 1 công đủ**, phần từ 17:00 đến 20:00 = tăng ca.
Không cộng dồn thành công lớn hơn 1.

### Lọc chấm liên tục
Công nhân hay chấm vân tay nhiều lần liên tiếp. Hệ thống gom các lần chấm trong cửa sổ **60 giây** thành
một, giữ lần **sớm nhất** làm giờ vào và lần **muộn nhất** làm giờ ra trong ngày.

### Tách OT trên sổ / OT ngoài (ATM) — Chủ chốt 2026-08-12

Code: `apps/api/app/modules/attendance/ot_split.py` · policy `payload.ot_split`.

| Quy tắc | Giá trị |
|---------|---------|
| Ngày áp dụng tách | **Thứ 3 và Thứ 5** (`isoweekday` 2, 4) |
| OT trên sổ (tính lương tháng) | **17:00 – 20:00** |
| OT ngoài / OT_EXT (trả ATM riêng) | **Sau 20:00** cùng ngày Th3/Th5 |
| Ngưỡng bấm ra được OT | **17:15** — bấm ra ≤ 17:15 → **0 phút OT** (grace toilet) |
| Số phút OT khi đủ điều kiện | Tính từ **17:00** (hết ca), không trừ 15 phút grace |
| Ngày khác Th3/Th5 | Toàn bộ OT sau 17:00 → **OT ngoài** (không lên sổ) |

**Ví dụ Thứ 3:** ra 17:10 → 0 OT · ra 17:16 → 16 phút OT sổ · ra 20:30 → 180p sổ + 30p ngoài.

Cấu hình trong `policy_packages.payload`:

```jsonc
"ot_split": {
  "on_books_weekdays": [2, 4],
  "on_books_after": "17:15",
  "on_books_until": "20:00",
  "ot_grace_minutes": 15
}
```

Xuất OT ngoài: module Chấm công → **OT ngoài** / API payroll `ot_external` — **không** gộp vào bảng lương tháng.

### Nếu Mitapro không có cột vào/ra
Suy: lần chấm đầu tiên trong ngày = vào, lần cuối = ra. Vì công ty **không có ca đêm**, cách suy
này an toàn. Vẫn nên xác minh (xem file 20 mục 20.8).

---

## 22.2 SỐ NGÀY CÔNG CHUẨN CỦA THÁNG (`divisor`)

Nguồn: `GenuiSuite_Logic.sql` dòng **13069–13073**.

```
divisor = COUNT(ngày trong tháng có DAY_TYPE <> 1)     -- số ngày làm việc theo lịch
IF divisor > 26 THEN divisor = 26
```

Đây là mẫu số dùng cho **toàn bộ** phép chia lương ngày, tăng ca, phụ cấp, lương nghỉ.

| Tháng | Ngày làm việc theo lịch | `divisor` |
|-------|------------------------|-----------|
| Tháng 27 ngày công | 27 | **26** (bị chặn trần) |
| Tháng 26 ngày công | 26 | 26 |
| Tháng Tết còn 20 ngày | 20 | **20** |

---

## 22.3 CHUYÊN CẦN VÀ ĐI LẠI

### Mức chuẩn — Chủ chốt
```
chuyên cần  = 600.000 đ
đi lại      = 800.000 đ
```

### Công thức chia
Nguồn: dòng **13946–13950**.

```
số ngày hưởng = WT_OFF + ALE + FLE + WED + HOL + COM
                (ngày công thực tế + nghỉ phép năm + nghỉ tang + nghỉ cưới
                 + nghỉ lễ + nghỉ bù)

tiền = mức chuẩn / divisor × số ngày hưởng
```

Mã `TMP` (nghỉ hết hàng) **không** nằm trong tử số — dòng tính có TMP đã bị đóng lại trong bản
đang chạy.

Phụ cấp chức vụ `POS_ALL` chia theo **đúng công thức này**.

### Kiểm chứng
| Tình huống | Phép tính | Kết quả |
|-----------|-----------|---------|
| Tháng 27 ngày, đi đủ 27 | 600.000 / 26 × 27 | **623.077** ✔ khớp phiếu gốc |
| Tháng 27 ngày, đi đủ 27 | 800.000 / 26 × 27 | **830.769** ✔ khớp phiếu gốc |
| Tháng 26 ngày, đi đủ | 600.000 / 26 × 26 | 600.000 |
| Tháng Tết 20 ngày, đi đủ 20 | 600.000 / 20 × 20 | **600.000** (vẫn đủ) |
| Tháng Tết 20 ngày, đi 15 | 600.000 / 20 × 15 | 450.000 |

### Tỷ lệ chuyên cần — nhân sau cùng
Nguồn: hàm `F_CAL_INDUS_AMT`, dòng **104–215**; áp dụng ở dòng **13961–13965**.

```
tỷ lệ = 1.00
NẾU (số lần trễ >= 3) HOẶC (số lần sớm >= 2)                    → tỷ lệ = 0.50
NẾU (số lần trễ >= 5) HOẶC (số lần sớm >= 4) HOẶC (có vắng)     → tỷ lệ = 0.00

tiền chuyên cần cuối = tiền đã chia × tỷ lệ
```

**Miễn trừ trễ/sớm** — không tính vào số lần trễ/sớm nếu ngày đó thỏa cả ba:
1. Có mã nghỉ thuộc `ALE`, `FLE`, `WED`
2. Số giờ nghỉ **dưới 8 giờ** (nghỉ nửa buổi)
3. Có chấm vân tay và `P_IN <= P_OUT`

**Ngày vắng** chỉ tính khi mã nghỉ **không thuộc** `ALE`, `FLE`, `WED`, `TMP`, `OFF`,
và ngày đó **sau khi hết thử việc** (`ABS_DT > ET_PROBATION`).

> ⚠️ Validator hiện tại đang sai ba chỗ, phải sửa:
> - Ngưỡng về sớm đang bị gộp chung với số ngày vắng → phải tách thành ba điều kiện độc lập
> - Mã miễn trừ đang là `AL / MARRIAGE / FUNERAL / HEALTHCHECK` → phải là `ALE / WED / FLE`
> - Thiếu điều kiện "nghỉ dưới 8 giờ và có quẹt thẻ"

### Thử việc
Dòng **13924–13937**: trong thời gian thử việc, các khoản sau **bằng 0**:
`TRAIN_ALL`, `POS_ALL`, `TECH_AMT`, `INDUS_AMT` (chuyên cần), `TRANS_AMT` (đi lại),
`TREAT_ALL`, `OTHER_AMT`, `SER_MONTH`, `SER_AMT` (thâm niên).

---

## 22.4 LƯƠNG NGÀY CÔNG

Nguồn: dòng **13276–13277**.

```
Chính thức:  (BASIC_SAL  + SAL_ALLOW) × số_ngày_công_chính_thức / divisor
Thử việc:    (PROB_SALARY + SAL_ALLOW) × số_ngày_công_thử_việc  / divisor
```

`PROB_SALARY` = **85%** lương chính thức (Chủ chốt).

Một người vào làm giữa tháng sẽ có cả hai dòng — đây là lý do mọi bảng chi tiết đều có cột
`segment` nhận giá trị `probation` hoặc `official`.

---

## 22.5 PHỤ CẤP THÂM NIÊN

Nguồn: hàm `F_CAL_SERVERANCE`, dòng **364–404**. Tham số là **số tháng làm việc**.

| Số tháng | Tiền |
|----------|------|
| < 6 | 0 |
| 6 – 119 | `FLOOR(số_tháng / 6) × 25.000` |
| 120 – 191 (10–15 năm) | 550.000 |
| 192 – 251 (16–20 năm) | 600.000 |
| 252 – 371 (21–30 năm) | 650.000 |
| ≥ 372 (từ 31 năm) | 700.000 |

Kiểm chứng: 136 tháng → 550.000 ✔ khớp phiếu gốc.

Số tháng tính bằng `FLOOR(MONTHS_BETWEEN(cuối_kỳ, ngày_vào_làm))`.

---

## 22.6 MƯỜI BỐN LOẠI NGHỈ

Nguồn: `Common_Codes.csv`, nhóm `HRAB0110`. Cột cuối là **% công ty trả lương**.

| Mã | Tên | % trả | Ghi chú |
|----|-----|-------|---------|
| `ALE` | Nghỉ phép năm | 100 | Miễn trừ chuyên cần |
| `FLE` | Nghỉ tang chế | 100 | Miễn trừ chuyên cần |
| `WED` | Nghỉ cưới | 100 | Miễn trừ chuyên cần |
| `LA` | Nghỉ tai nạn lao động | 100 | |
| `OFF` | Nghỉ bù | 100 | Không tính là vắng |
| `TMP` | Nghỉ hết hàng | **70** | Không tính là vắng, nhưng **không** vào tử số chia phụ cấp |
| `PT` | Nghỉ khám thai | 0 | BHXH chi trả |
| `MLE` | Nghỉ thai sản | 0 | BHXH chi trả |
| `MC` | Nghỉ sẩy thai | 0 | BHXH chi trả |
| `SLE` | Nghỉ ốm | 0 | BHXH chi trả |
| `SCH` | Nghỉ con ốm | 0 | BHXH chi trả |
| `NOP` | Nghỉ không phép | 0 | **Tính là vắng** → mất sạch chuyên cần |
| `NON` | Không chấm công | 0 | **Tính là vắng** |
| `PER` | Nghỉ có phép | **chưa đặt** | GenusSuite bỏ trống — **buộc HR khai báo**, không được đoán |

### Tiền lương ngày nghỉ
Nguồn: dòng **13811**.
```
tiền = (BASIC_SAL + SAL_ALLOW) / divisor × số_ngày_nghỉ × (% trả lương / 100)
```
Mỗi loại nghỉ là **một dòng riêng** trên phiếu lương, không gộp vào lương ngày công.

---

## 22.7 PHÉP NĂM

```
Số ngày một năm: 14
Tích lũy:        round(số_tháng × 14 / 12, 2)
Mốc tính:        người cũ từ 01/01; người mới từ ngày vào làm
```
Kiểm chứng: đến hết tháng 8 → `round(8 × 14/12, 2)` = **9,33 ngày** ✔ khớp phiếu gốc.

Phép năm lưu dạng **sổ bút toán** (`annual_leave_ledger` + `annual_leave_entries`), không phải
một con số tính lại mỗi lần gọi. Ba số in trên phiếu lương (được cấp / đã dùng / còn lại) là kết
quả cộng dồn các dòng bút toán.

### Trả tiền phép chưa dùng khi nghỉ việc
Nguồn: dòng **8346** và **12900**.
```
tiền phép tồn = (BASIC_SAL + SAL_ALLOW) / 26 × số_ngày_phép_chưa_dùng
```
Chú ý: chỗ này GenusSuite dùng **26 cố định**, không dùng `divisor`.

---

## 22.8 TĂNG CA

### Nền tính tăng ca
Nguồn: dòng **13281**. **Khác** nền tính bảo hiểm.
```
OT_base = BASIC_SAL + POS_AMT + TECH_AMT + TREAT_ALLOW
        + SER_AMT + TRAIN_ALLOW + INDUS_ALLOW
```

### Công thức
```
tiền OT = OT_base × số_giờ × hệ_số / divisor / 8
```

| Loại | Hệ số | Nguồn |
|------|-------|-------|
| Tăng ca ngày thường | **1,5** | dòng 13281 |
| Chủ nhật (`ST`) | **2,0** | dòng 13319 |
| Ngày lễ (`HT`) ≤ 8 giờ | **2,0** | dòng 13307 |
| Ngày lễ (`HT`) > 8 giờ | `8 × 2 + (giờ − 8) × 3` | dòng 13308 |
| Phụ cấp ca đêm `NT30/45/60` | **0,3** | dòng 13291, 13296, 13301 |

> Ghi chú trong mã nguồn gốc: *"o il jung chi tro cap 30% cho ca dem"* — công ty chỉ trả 30% cho
> ca đêm ở cả ba mức. Hiện **không dùng** vì không có ca đêm, nhưng giữ trong thiết kế.

### Làm tròn
Tăng ca tính theo **bậc 30 phút**, làm tròn xuống. Tối thiểu 30 phút mới được tính.

---

## 22.9 BẢO HIỂM VÀ CÔNG ĐOÀN

### Nền đóng bảo hiểm
Nguồn: dòng **13415–13420**. **Khác** nền tính tăng ca — không có `INDUS_ALLOW` và `TRANS`.
```
SI_base = BASIC_SAL + POS_AMT + TECH_AMT + SER_AMT + TRAIN_ALLOW + TREAT_ALLOW
IF SI_base >= 46.800.000 THEN SI_base = 46.800.000      -- trần
```

> **Chuyên cần và đi lại KHÔNG tính vào nền đóng bảo hiểm. Thâm niên thì CÓ.**
> Kiểm chứng phiếu MSNV 1519: lương ngày công 8.335.000, nền BHXH 8.885.000, chênh đúng 550.000
> = phụ cấp thâm niên. ✔

### Tỷ lệ
| Khoản | Tỷ lệ |
|-------|-------|
| BHXH | 8% |
| BHYT | 1,5% |
| BHTN | 1% |
| Công đoàn | 44.100 đ (số cố định) |

Cả bốn phải nằm trong bảng `insurance_rates` có ngày hiệu lực, không viết cứng.

---

## 22.10 THU NHẬP CHỊU THUẾ ≠ THỰC LÃNH

```
Tổng thu nhập      = lương ngày công + lương ngày nghỉ + tăng ca + toàn bộ phụ cấp
Thu nhập chịu thuế = Tổng thu nhập − bảo hiểm bắt buộc
Thu nhập tính thuế = Thu nhập chịu thuế − giảm trừ bản thân − giảm trừ người phụ thuộc
Thực lãnh          = Tổng thu nhập − toàn bộ khấu trừ (gồm cả thuế, tạm ứng, khoản trừ khác)
```

Trên phiếu tháng 7/2026 hai số cuối trùng nhau ở 9.682.398 **chỉ vì thuế kỳ đó bằng 0**. Phải
lưu **ba cột riêng**: `gross`, `taxable_income`, `net`, cộng `family_deduction` để lưu vết mức
giảm trừ đã áp.

Giảm trừ hiện hành: bản thân 11.000.000 đ, mỗi người phụ thuộc 4.400.000 đ. Số người phụ thuộc
**tính ra** từ bảng `employee_family_members`, không nhập tay.

---

## 22.11 BÀI KIỂM CHỨNG BẮT BUỘC — MSNV 1519, kỳ 07/2026

Tính lại bằng engine mới phải ra **đúng từng đồng**:

| Bước | Phép tính | Kết quả |
|------|-----------|---------|
| Đơn giá ngày | 8.335.000 ÷ 26 | 320.577 |
| Lương ngày công | 26,0 × 320.577 | 8.335.000 |
| Phép năm 1 ngày | 1,0 × 320.577 × 100% | 320.577 |
| Tổng trợ cấp | 623.077 + 830.769 + 550.000 | 2.003.846 |
| **Tổng thu nhập** | 8.335.000 + 320.577 + 2.003.846 | **10.659.423** |
| Nền BHXH | 8.335.000 + 550.000 | 8.885.000 |
| BHXH | 8.885.000 × 8% | 710.800 |
| BHYT | 8.885.000 × 1,5% | 133.275 |
| BHTN | 8.885.000 × 1% | 88.850 |
| Công đoàn | cố định | 44.100 |
| Tổng khấu trừ | cộng bốn khoản trên | 977.025 |
| **Thực lãnh** | 10.659.423 − 977.025 | **9.682.398** |

Không khớp một đồng nào cũng là **chưa đạt**.

---

## 22.12 CẤU HÌNH ĐI VÀO `policy_packages.payload`

Toàn bộ số ở file này phải nằm trong payload hoặc bảng danh mục, **không viết cứng**.

```jsonc
{
  "attendance_bonus_monthly": 600000,
  "transport_monthly_default": 800000,
  "probation": { "salary_percent": 85, "zero_allowances": true },

  "divisor_rule": { "source": "calendar_working_days", "cap": 26 },

  "allowance_proration": {
    "numerator": ["WT", "ALE", "FLE", "WED", "HOL", "COM"],
    "formula": "base / divisor * numerator_days"
  },

  "attendance_penalties": {
    "late_half": 3, "early_half": 2,
    "late_zero": 5, "early_zero": 4,
    "any_absence_zero": true,
    "exempt_leave_codes": ["ALE", "FLE", "WED"],
    "exempt_requires_hours_lt": 8,
    "exempt_requires_punch": true,
    "ignore_absence_during_probation": true
  },

  "work_time": {
    "standard_shift": { "start": "08:00:00", "end": "17:00:00" },
    "lunch_deduct_hours": 1,
    "punches_per_day": 2,
    "night_shift_enabled": false,
    "late_grace_seconds": 0,
    "early_grace_seconds": 0,
    "punch_dedupe": { "window_seconds": 60 }
  },

  "ot_rates": { "weekday": 1.5, "sunday": 2.0, "holiday": 2.0,
                "holiday_over_8": 3.0, "night_addon": 0.3 },
  "ot_split": {
    "on_books_weekdays": [2, 4],
    "on_books_after": "17:15",
    "on_books_until": "20:00",
    "ot_grace_minutes": 15
  },
  "ot_base_components": ["BASIC","POS","TECH","TREAT","SENIORITY","TRAIN","INDUS"],

  "si_rates": { "bhxh": 0.08, "bhyt": 0.015, "bhtn": 0.01 },
  "si_base_components": ["BASIC","POS","TECH","SENIORITY","TRAIN","TREAT"],
  "si_base_cap": 46800000,
  "union_fee_default": 44100,

  "annual_leave": { "days_per_year": 14, "accrual_mode": "monthly_prorated",
                    "accrual_round_digits": 2, "payout_divisor": 26 },

  "pit_personal_deduction": 11000000,
  "pit_dependent_deduction": 4400000,

  "rounding": { "money_unit": 1, "money_mode": "half_up",
                "hours_step_minutes": 30, "hours_mode": "floor",
                "day_fraction_digits": 2 }
}
```

`validate_payload` hiện đã gộp payload người dùng lên `default_payload()` trước khi kiểm tra —
giữ nguyên cơ chế đó, gói cũ thiếu khóa mới vẫn chạy được.

**Ba luật khi thêm khóa:** chỉ thêm không đổi tên · khóa mới ảnh hưởng tiền thì mặc định tắt ·
`policy_snapshots` là bất biến, thêm khóa về sau không hồi tố vào ảnh chụp cũ.

---



---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
*Tiếp: `23_UI_MAN_HINH.md`*
