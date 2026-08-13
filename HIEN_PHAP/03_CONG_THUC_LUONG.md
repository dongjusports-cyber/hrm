# 03 — Công thức lương & Policy (chuẩn đối chiếu Excel)

> Mọi hằng số dưới đây là **SEED mặc định** (từ Excel 2025 + `Cách tính lương.docx`).  
> Runtime: đọc từ Policy Engine — **không hard-code trong code tính lương**.

---

## 3.1 Kỳ lương & chi trả

| Hạng mục | Quy tắc |
|----------|---------|
| Kỳ tính công/lương | **Ngày 01 → ngày cuối tháng** |
| Ngày chi trả | **Ngày 08 tháng sau** (nếu trùng nghỉ → sớm hoặc muộn 1 ngày — Admin cấu hình) |
| Đơn vị tiền | VND, làm tròn theo policy (mặc định: đồng, 0 chữ số thập phân khi xuất thực lãnh) |

## 3.2 Mẫu số chia lương (Salary Divisor) — AUTO

### Bước 1 — Đếm ngày công chuẩn tháng từ Lịch công ty
- Mặc định: Thứ 2–Thứ 7 là ngày công (Admin cấu hình)
- Trừ Chủ nhật + ngày lễ (catalog Admin)

Gọi: `official_work_days` = số ngày công chuẩn tháng.

### Bước 2 — Áp rule mẫu số (seed — Admin sửa được)

```
IF official_work_days == 27:
    salary_divisor = 26
ELSE:
    salary_divisor = official_work_days
```

Đã kiểm chứng Excel:

| Tháng | Ngày công chuẩn phổ biến | Mẫu số thực tế |
|-------|--------------------------|----------------|
| 09/2025 | 26 | **26** |
| 10/2025 | 27 | **26** |
| 11/2025 | 25 | **25** |
| 12/2025 | 26–27 | **26** |

### Công thực tế từng NV

| Ký hiệu | Ý nghĩa | Nguồn |
|---------|---------|-------|
| `worked_days` | Công thực tế (cột O Excel, có thể lẻ 26.8125) | Mitapro / HR điều chỉnh |
| `al_days` | Nghỉ phép năm (cột P) — **có lương** | HR / đơn từ |
| `rem_days` | Nghỉ chế độ (cột Q) — **công ty không trả lương**; nếu có BH thì BH trả; **không** tính nghỉ không phép | HR |
| `probation_days` | Ngày công thử việc | Hệ thống theo ngày ký HĐ |

**Thử việc:** dùng lương thử việc đến **ngày ký HĐ chính thức** (cột J Excel / `contract_signed_at`).

## 3.3 Lương ngày công (WD Salary)

```
paid_days = worked_days + al_days       # (giá trị FULL precision, KHÔNG làm tròn số ngày)

# NV có cả giai đoạn thử việc + chính thức trong tháng thì cộng 2 phần:
wd_salary = contract_salary  / salary_divisor * (official_days + al_days)
          + probation_salary / salary_divisor * probation_days
```

**Khớp Excel Oct/2025** với `salary_divisor=26` (ĐÃ XÁC MINH).
- NV thử việc thuần (vd MSNV 8682): `4.840.750/26*19 = 3.537.471đ` ✓
- NV chính thức (vd MSNV 5290): `5.675.000/26*27 = 5.893.269đ` ✓

> **⚠️ Độ chính xác số ngày (ĐÃ CHỐT):** `worked_days` giữ **đủ precision từ phút chấm công** (vd 25.78125). File Excel từ **GenuiSuite** (HRM Hàn Quốc, chạy từ ~2015) hay cắt 4 chữ số → lệch ~10đ/người. **DJ HRM không bắt chước cách làm tròn cũ** — dùng Decimal hiện đại, chỉ làm tròn ĐỒNG ở bước cuối (xem `13_TEST...`).

> **REM (nghỉ chế độ):** mặc định **không** cộng vào `paid_days`. **NGOẠI LỆ đã phát hiện** (MSNV 5122, 6300 tháng 10): một số ca REM lại được tính công đủ tháng → **CHỜ Chủ hỏi NV tính lương** rồi cập nhật policy. Không chặn dựng code; khi có câu trả lời sẽ chỉnh cờ `paid_by_company` theo loại REM.

## 3.4 Catalog phụ cấp (Allowances)

Mỗi loại phụ cấp là 1 record metadata:

| Field | Ý nghĩa |
|-------|---------|
| `code` | `ATTEND`, `TRANSPORT`, `TOXIC`, `SENIORITY`, `POSITION`, `TECH`, `CHILD`, `PCCC`, `OTHER`… |
| `monthly_amount` hoặc rule | Số tiền tháng / công thức bậc |
| `proration` | `by_worked_days` \| `full_if_eligible` \| `fixed` |
| `include_in_si_base` | Có cộng vào **Lương đóng BH** không (dùng **giá trị đầy đủ**, không prorate) |

### Cờ tính base — SEED (ĐÃ XÁC MINH bảng lương T10 + NV Bảo hiểm)

Có **2 cờ độc lập**: `include_in_si_base` (base khấu trừ BH) và `include_in_ot_base` (base tính OT).

| Phụ cấp | `code` | Cột Excel | `include_in_si_base` | `include_in_ot_base` |
|---------|--------|-----------|:--------------------:|:--------------------:|
| Chức vụ | `POSITION` | C20 | ✅ | ✅ |
| Độc hại | `TOXIC` | C21 | ✅ | ✅ |
| PCCC+HSE | `PCCC` | C23 | ✅ | ✅ |
| Tay nghề may | `TECH` | C24 | ✅ | ✅ |
| Thâm niên | `SENIORITY` | C25 | ✅ | ✅ |
| **Chuyên cần** | `ATTEND` | C19 | ❌ | ✅ (mức chuẩn) |
| **Đi lại** | `TRANSPORT` | C22 | ❌ | ❌ |
| **Khác** | `OTHER` | C26 | ❌ | ❌ |
| Con nhỏ | `CHILD` | — | ❌ | ❌ (mặc định) |

> Điểm khác biệt duy nhất: **Chuyên cần** vào base OT nhưng KHÔNG vào base BH. Admin đổi cờ khi quy định thay đổi — **không sửa code**.

### Seed từ tài liệu & Excel

#### A) Chuyên cần (`ATTEND`) — mặc định 230.000đ/tháng (Admin đổi được → 630k…)

**Điều kiện nhận đủ (seed từ doc):**
- Không nghỉ ngày làm việc trong tháng (trừ các ngoại lệ dưới) → 100%

**Vẫn được tính chuyên cần (không phạt vì các lý do sau):**
- Nghỉ phép năm
- Nghỉ kết hôn theo luật
- Nghỉ tang theo luật
- Nghỉ khi công ty gửi khám sức khỏe

**Trừ theo ngày nghỉ / về sớm (seed doc — nhóm nghỉ bệnh, khám bệnh trong giờ, không phép, phép không lương):**

| Điều kiện | % còn lại |
|-----------|-----------|
| Nghỉ 1 ngày **hoặc** về sớm 2 lần / tháng | **50%** |
| Nghỉ ≥ 2 ngày / tháng | **0%** (trừ 100%) |

**Trừ theo đi trễ (seed doc):**

| Số lần đi trễ / tháng | % còn lại |
|----------------------|-----------|
| 3–4 lần | **50%** |
| ≥ 5 lần | **0%** |

**Quyết định hội thoại (có thể tạo Policy gói “mùa cao điểm”):**
- Chủ từng mô tả: trễ 1 lần = 50%, 2 lần = mất hết; trễ+sớm **cộng chung**.
- Hệ thống phải hỗ trợ **nhiều gói policy** (mùa). Seed mặc định khi cài = **theo `Cách tính lương.docx`**. Gói khác Admin tự tạo.

**Pro-rata tiền chuyên cần gốc (khớp Excel):**

```
attend_raw = attend_monthly_amount / salary_divisor * worked_days
attend_final = attend_raw * (remaining_percent / 100)
```

Trong đó `remaining_percent` sau khi áp bậc phạt (lấy mức phạt nặng nhất nếu nhiều rule cùng áp — **configurable**: `penalty_combine_mode = max | multiply`).

#### B) Đi lại (`TRANSPORT`)

```
transport = transport_monthly / salary_divisor * worked_days
```

Seed Excel tháng đủ: ~760.000đ/tháng.

> Doc ghi mẫu `/26` — runtime dùng `salary_divisor` của tháng (không hard 26).

#### C) Độc hại (`TOXIC`)
- Seed: 100.000đ (công nhân xưởng đủ điều kiện) — Admin cấu hình theo tổ/chức danh.

#### D) Thâm niên (`SENIORITY`) — seed doc

| Thâm niên | Số tiền/tháng |
|-----------|---------------|
| Đủ 6 tháng → dưới 10 năm | 25.000đ + thêm 25.000 mỗi đủ 6 tháng |
| 10–15 năm | 550.000 |
| 15–20 năm | 600.000 |
| 20–30 năm | 650.000 |
| > 30 năm | 700.000 |

(Implement: hàm tính từ `join_date` → bậc; Admin sửa bảng bậc.)

#### E) Con nhỏ (`CHILD`)
- Nữ có con 0–6 tuổi: **100.000đ / tháng / con** (không giới hạn số con)
- Cần giấy khai sinh trong hồ sơ

#### F) Chức vụ / Kỹ thuật / PCCC+HSE / Tay nghề may / Other
- Theo catalog + gán theo NV hoặc chức danh (Excel cột Position, Tech, PCCC…)

#### G) Tổng phụ cấp

```
allowance_total = SUM(các phụ cấp đủ điều kiện sau pro-rata / phạt)
```

## 3.5 Tăng ca (OT)

### Hệ số (seed — Luật LĐ + doc công ty)

| Loại | Hệ số tối thiểu | `ot_type` |
|------|-----------------|-----------|
| Ngày thường | **150%** | `weekday` |
| Ngày nghỉ tuần (CN) | **200%** | `weekend` |
| Lễ / nghỉ có lương | **300%** | `holiday` |
| Làm đêm 22:00–06:00 | +**30%** lương giờ ngày | `night_addon` |
| OT ban đêm | thêm **20%** theo quy định khoản 3 Điều 06 | `ot_night_extra` |

Giờ làm chuẩn: **08:00–12:00, 13:00–17:00** (8 giờ). OT ngày thường thường đến ~20:00.

> **MVP (vừa đủ):** nhà máy hiện gần như chỉ có **OT ngày thường 150%**. `night_addon` / `ot_night_extra` để **tắt mặc định** (hệ số vẫn có trong catalog), chỉ bật khi thực sự phát sinh ca đêm — tránh phức tạp không cần thiết.

### Base tính OT — ĐÃ CHỐT (xác minh 99.7% — 295/296 NV có OT tháng 10)

> ⚠️ **QUAN TRỌNG — base OT ≠ base khấu trừ BH.** Đây là 2 số khác nhau:

```
ot_base = contract_salary + Σ allowance_full[i]  WHERE include_in_ot_base[i] = TRUE
        = si_contribution_base + chuyên cần (giá trị chuẩn, vd 230.000đ)

ot_hourly_base = ot_base / salary_divisor / 8
ot_pay         = Σ ( ot_hours[type] * ot_hourly_base * ot_rate[type] )
```

- `include_in_ot_base` = TRUE cho: Chức vụ, Độc hại, PCCC+HSE, Tay nghề, Thâm niên **và Chuyên cần** (dùng mức chuẩn, không phải mức đã bị phạt).
- FALSE cho: Đi lại, Khác.
- Dùng **giá trị đầy đủ** của phụ cấp (KHÔNG prorate).

> **ĐÃ XÁC MINH** — VD MSNV 5290 (OT 27h): base = `6.325.000 (mức đóng BH) + 230.000 (chuyên cần) = 6.555.000`; `6.555.000/26/8*1.5*27 = 1.276.334đ` = đúng số Excel.
> Nếu dùng nhầm mức đóng BH (6.325.000) làm base OT → **khớp 0%** (lệch ~45k/người). Đây là lỗi phải tránh tuyệt đối.

**`si_contribution_base` (Lương đóng BH, dùng cho khấu trừ BH)** = **TỰ TÍNH**:

```
si_contribution_base = contract_salary (hoặc probation_salary nếu thử việc)
                     + Σ allowance_full[i]  WHERE include_in_si_base[i] = TRUE
```

- Bao gồm: Chức vụ, Độc hại, PCCC+HSE, Tay nghề, Thâm niên. **KHÔNG** gồm Chuyên cần, Đi lại, Khác.
- Xác minh 320 NV + nhân viên Bảo hiểm xác nhận. VD 5290: `5.675.000 + 100.000 + 550.000 = 6.325.000` = đúng BHXH thực.

> **File `DS Lương CB.xlsx`** = chính là **base OT** (= mức đóng BH + chuyên cần). Dùng để đối chiếu khi import; `si_base_override` cho ca ngoại lệ.

Excel hiện chủ yếu cột **OT ngày thường (150%)**; hệ thống hỗ trợ tách loại giờ (weekend/holiday/đêm) từ Mitapro + lịch khi phát sinh.

## 3.6 Tổng thu nhập (Gross)

```
gross = wd_salary + allowance_total + ot_pay + other_adjustments
```

`other_adjustments` = **1 catalog gộp** cho mọi khoản cộng/trừ bất thường (Re-Pay tháng 9, truy lĩnh, bù trừ…). **MVP không tách module Re-Pay riêng** — dùng chung 1 danh mục điều chỉnh, đủ dùng và gọn.

## 3.7 Bảo hiểm & công đoàn (phía NLĐ)

```
bhxh = si_contribution_base * rate_bhxh   # seed 8%
bhyt = si_contribution_base * rate_bhyt   # seed 1.5%
bhtn = si_contribution_base * rate_bhtn   # seed 1.0%
union_fee = union_fee_amount              # seed ~44.100đ (Admin)
```

Trần/sàn BHXH theo luật — Admin cập nhật khi NĐ thay đổi.

**NV thử việc / CASH mới:** có thể BH = 0 (khớp sheet CASH Excel) — flag `si_enrolled`.

## 3.8 Thực lãnh (Net)

```
net = gross - bhxh - bhyt - bhtn - union_fee - other_deductions
```

`other_deductions` = tạm ứng, phạt… (catalog).

### TNCN
**Phase 2** — không tính trong MVP. Để cột `pit_amount = 0`, module sẵn sàng bật sau.

## 3.9 Thưởng cuối năm (Tết) — seed doc

```
IF tenure_months >= 12:
    bonus = contract_salary * 1
ELSE:
    bonus = contract_salary / 12 * tenure_months
```

Chạy như khoản đặc biệt (không trộn vào kỳ lương tháng thường trừ khi Admin bật).

## 3.10 Phân loại chi trả

| Kênh | Điều kiện |
|------|-----------|
| ATM | Có số TK ngân hàng |
| CASH | Không TK / NV mới theo quy tắc HR |

## 3.11 Pipeline tính lương (Engine)

```
1. Mở kỳ (year-month) → CalendarEngine.compute(divisor)
2. Sync / khóa bảng công kỳ
3. Load employees + policy_version snapshot
4. For each employee:
     compute wd_salary
     compute allowances (+ attendance penalties)
     compute ot
     compute gross
     compute insurance
     compute net
5. Ghi payslip_lines + payslip_header + policy_snapshot_id
6. HR review → Publish → Worker thấy
7. Confirm / Dispute
8. Khóa kỳ (không sửa trừ Admin mở lại có log)
```

## 3.12 Cột bảng lương (map Excel)

| Excel | Field hệ thống |
|-------|----------------|
| MSNV | `employee_code` |
| Tổ | `section_code` |
| Lương HĐ | `contract_salary` |
| Lương thử việc | `probation_salary` |
| OFF C / Total / AL / REM | `official_days` (ref), `worked_days`, `al_days`, `rem_days` |
| Lương ngày công | `wd_salary` |
| Phụ cấp * | `allowance_*` |
| Giờ TC / Tiền OT | `ot_hours_*`, `ot_pay` |
| Tổng thu nhập | `gross` |
| BHXH/BHYT/BHTN/CD | `si_*`, `union_fee` |
| Khấu trừ | `deductions` |
| Thực lãnh | `net` |

## 3.13 Regression bắt buộc

Trước khi Go-live lương: chạy lại **tháng 10/2025** (331 NV), so khớp Excel:

- `wd_salary`, `allowance` pro-rata, `si_*`, `gross`, `net`
- Cho phép lệch làm tròn ≤ 1–2đ; lệch lớn phải log giải thích (case ngoại lệ)



---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
*Tiếp: `04_CHAM_CONG_AGENT.md`*
