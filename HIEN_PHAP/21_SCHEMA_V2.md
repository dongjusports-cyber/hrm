# 21 — SCHEMA V2

> Đọc cùng file 20. Mọi bảng mới đều là `snake_case` số nhiều, khớp quy ước đang có.

---

## 21.1 BA MƯƠI MỐT BẢNG ĐÃ CÓ — CẤM DỰNG LẠI

Grep mã nguồn ngày 2026-08-10. Trước khi tạo bất kỳ bảng nào, đối chiếu danh sách này.

| Module | Bảng |
|--------|------|
| `mdm` | `departments`, `employees`, `employee_violations`, `employee_documents` |
| `core` | `users`, `user_module_grants`, `user_permissions`, `export_logs` |
| `integration` | `sync_jobs`, `attendance_punches` |
| `audit` | `audit_logs` |
| `dispute` | `disputes` |
| `attendance` | `attendance_days`, `leave_types`, `pay_periods`, `timesheet_months`, `timesheet_adjustments` |
| `config` | `portal_tabs` |
| `ai` | `ai_alerts`, `ai_runtime_settings`, `ai_jobs` |
| `policy` | `policy_packages`, `policy_confirm_logs` |
| `payroll` | `allowance_types`, `employee_allowance_assignments`, `policy_snapshots`, `payroll_runs`, `payslip_adjustments`, `payslips` |
| `calendar` | `holidays`, `work_week_rules` |

**Lưu ý dễ nhầm:**

- Bảng kỳ lương tên thật là **`pay_periods`**, không phải `payroll_periods`.
- **`holidays` đã tồn tại** trong module `calendar` — chỉ mở rộng, không tạo mới.
- **`employee_violations` đã tồn tại** — đây chính là bảng kỷ luật, dùng lại.
- **`user_permissions` + `user_module_grants` đã tồn tại** — quyền theo từng người. V2 thêm
  `roles` + `role_permissions` làm lớp vai trò, giữ hai bảng cũ làm lớp ghi đè cá nhân.
- `allowance_types` đã tồn tại — `pay_components` là bản mở rộng của nó, **đổi tên và thêm cột**,
  không tạo bảng song song.

---

## 21.2 NHÓM TỔ CHỨC

### `departments` — MỞ RỘNG
```
+ name_local        varchar(200)
+ dept_type         varchar(20)     -- office | factory | support
+ sort_order        int
+ effective_from    date NOT NULL
+ effective_to      date NULL
```
`is_active` hiện có chuyển thành cột suy ra (`effective_to IS NULL OR effective_to >= today`),
**không lưu**. 10 bộ phận thật lấy từ `TCO_EODEPT`.

### `teams` — MỚI
```
id                  PK
department_id       FK departments NOT NULL
code                varchar(30) NOT NULL
name                varchar(200) NOT NULL
name_local          varchar(200)
default_shift_id    FK work_shifts NULL
sort_order          int
effective_from      date NOT NULL
effective_to        date NULL
UNIQUE (department_id, code)
```
73 tổ, nguồn `THR_ABWORKGRP`. Đây là cấp mà công nhân thực sự thuộc về.

### `positions` — MỚI
```
code PK varchar(20) · name · name_local · level int · is_management bool · sort_order
```
52 chức vụ, nguồn `HRAB0060`.

### `jobs` — MỚI
```
code PK varchar(20) · name · name_local · is_hazardous bool · sort_order
```
82 mã công việc, nguồn `HRAB0100`. **Tách rời chức vụ** — GenusSuite có cả hai, DJ HRM đang gộp.

---

## 21.3 NHÓM HỒ SƠ

### `employees` — MỞ RỘNG (18 cột)
```
+ team_id               FK teams NOT NULL      -- thay department_id
+ position_code         FK positions
+ job_code              FK jobs
+ birth_date            date
+ birth_place_code      varchar(20)
+ nationality_code      varchar(20)
+ ethnicity_code        varchar(20)
+ religion_code         varchar(20)
+ marital_status        varchar(20)
+ children_count        smallint DEFAULT 0
+ education_code        varchar(20)
+ id_issue_date         date
+ id_issue_place_code   varchar(20)
+ permanent_address     text
+ temporary_address     text
+ urgent_contact        varchar(200)
+ ~~timekeeping_card_no~~  (đã bỏ — dùng vân tay Mitapro, map qua MSNV/MaChamCong)
+ si_book_no            varchar(40)
```
Bỏ `department_id`. Bộ phận suy ra qua `teams.department_id` — **không lưu hai chỗ**.

### `labour_contracts` — MỚI
```
id · employee_id FK · contract_type_code · seq_no smallint
sign_date date · start_date date · end_date date NULL
base_salary numeric(14,2) · position_code · team_id
status varchar(20)   -- draft | active | expired | terminated
file_path text
INDEX (employee_id, start_date) · INDEX (end_date) WHERE status='active'
CHECK: không chồng lấn khoảng ngày trên cùng employee_id
```
Bốn bậc: thử việc → HĐ 1 năm lần 1 → HĐ 1 năm lần 2 → vô thời hạn.

### `employee_assignments` — MỚI
```
id · employee_id FK · team_id FK · position_code · job_code
effective_from date NOT NULL · effective_to date NULL
decision_no varchar(50) · reason_code · approved_by FK users
INDEX (employee_id, effective_from)
```
Lịch sử đổi tổ / chức vụ. **Không có bảng này thì in lại bảng lương cũ sẽ ra sai tổ.**

### `employee_family_members` — MỚI
```
id · employee_id FK · relationship_code · full_name · birth_date · id_number
is_tax_dependent bool · dependent_from date · dependent_to date
```
6 quan hệ: cha, mẹ, con, chị, anh, khác. Số người phụ thuộc **tính ra** từ bảng này, không nhập tay.

### `employee_resignations` — MỚI
```
id · employee_id FK · seq_no smallint
resign_type_code · applied_date · last_working_date
reason text · severance_months int · severance_amount numeric(14,2)
handover_done bool · rehired_at date NULL
UNIQUE (employee_id, seq_no)
```
**KHÔNG unique theo `employee_id`.** Công nhân nghỉ rồi vào lại là chuyện thường ở xưởng may.
5 lý do: trong thử việc · nộp đơn · tự ý bỏ việc · hết hạn HĐ · sa thải.

### `employee_salary_history` · `employee_allowance_history` — MỚI
```
id · employee_id FK · effective_from date · old_value numeric · new_value numeric
decision_no · approved_by · note
INDEX (employee_id, effective_from)
```

### `employee_educations` · `employee_experiences` · `employee_health_checks` — MỚI
Ba bảng con, mỗi bảng một tab trong form hồ sơ. `INDEX (employee_id)`.

### `insurance_declarations` — MỚI
```
id · employee_id FK
declaration_type varchar(20)   -- increase | decrease | salary_change
effective_month  char(7)       -- YYYY-MM
old_salary numeric(14,2) · new_salary numeric(14,2)
reason_code · batch_no varchar(30) · submitted_at · status varchar(20)
INDEX (effective_month, status)
```
Nguồn `THR_INSURANCE_C47` (0=tăng, 1=giảm, 2=đổi lương). Việc HR làm hàng tháng, có deadline
với cơ quan bảo hiểm.

---

## 21.4 NHÓM DANH MỤC & CHÍNH SÁCH

### `lookup_values` — MỚI
```
group_code varchar(30) · code varchar(30) · name · name_local · sort_order · is_active
UNIQUE (group_code, code)
```
Chỉ cho danh mục **phẳng, không mang quy tắc**: dân tộc, tôn giáo, quốc tịch, nơi sinh, nơi cấp
CCCD, trình độ. Danh mục **có quy tắc** phải có bảng riêng — không lặp lại sai lầm `TCO_ABCODE`
của GenusSuite (2.609 mã trộn 427 nhóm trong một bảng).

### `leave_types` — MỞ RỘNG
```
+ pay_ratio_percent        smallint    -- 0 | 70 | 100
+ paid_by_si               bool        -- BHXH chi trả, không phải công ty
+ affects_attendance_bonus bool
+ counts_as_worked_day     bool        -- có vào tử số chia phụ cấp không
+ requires_document        bool
+ max_days_per_year        smallint NULL
```
Thêm 10 mã còn thiếu. Bảng đầy đủ 14 mã ở file 22 mục 22.6.

### `work_shifts` — MỚI
```
code PK · name · start_time · end_time
lunch_start · lunch_end · dinner_start · dinner_end
ot_start · night_start
lunch_deduct_hours numeric(3,1) · dinner_deduct_hours numeric(3,1)
standard_hours numeric(3,1)
```
Thực tế công ty **chỉ dùng 1 ca hành chính** `08:00–17:00`, nghỉ trưa `12:00–13:00`, trừ 1 giờ.
Bảng vẫn dựng đủ để sau này thêm ca mà không phải migration.

### `team_shift_schedules` — MỚI
```
team_id FK · work_date date · work_shift_id FK · note
UNIQUE (team_id, work_date)
```
Xếp ca **theo tổ**, không theo từng người.

### `holidays` — MỞ RỘNG (bảng đã có)
```
+ day_property varchar(10)   -- full | half
+ pay_ratio    smallint
+ is_paid      bool
```

### `holiday_scopes` — MỚI
```
holiday_id FK · department_id FK NULL · team_id FK NULL
```
Không có dòng nào = áp toàn công ty.

### `pit_brackets` · `pit_deductions` — MỚI
```
pit_brackets:   effective_from date · seq · from_amount · rate_percent
                UNIQUE (effective_from, seq)
pit_deductions: effective_from date · self_amount · dependent_amount
```
7 bậc. **Có ngày hiệu lực** — chỗ GenusSuite làm sai (`THR_TAX` không có, đổi biểu thuế là hỏng
số cũ).

### `insurance_rates` — MỚI
```
effective_from date UNIQUE
si_employee_pct · hi_employee_pct · ui_employee_pct · union_pct
si_base_cap numeric(14,2) · region_min_wage numeric(14,2)
```
Hiện hành: 8% / 1,5% / 1% · trần 46.800.000 · công đoàn 44.100 đ.

### `seniority_allowance_tiers` — MỚI
```
effective_from date · months_from int · months_to int NULL · amount numeric(14,2)
```
Bậc đầy đủ ở file 22 mục 22.5.

### `attendance_bonus_rules` — MỚI
```
effective_from date
late_count_half · early_count_half · late_count_zero · early_count_zero
exempt_leave_codes text[]  -- ['ALE','WED','FLE']
full_amount numeric(14,2)
```

### `pay_components` — MỞ RỘNG từ `allowance_types`
```
+ kind             varchar(20)   -- earning | deduction | info
+ affects_si_base  bool
+ affects_ot_base  bool
+ affects_pit      bool
+ proration_rule   varchar(30)   -- none | by_worked_days | by_calendar_days
```
Đổi tên bảng `allowance_types` → `pay_components`, giữ dữ liệu. Thêm khoảng 30 mã suy ra từ 148
cột bảng lương cũ.

### `ot_exemptions` — MỚI
```
employee_id FK · exemption_code varchar(10)   -- PRE | TEN
valid_from date · valid_to date · evidence_path text
```
PRE = mang thai trên 7 tháng · TEN = đang nuôi con nhỏ. Nhóm không được huy động tăng ca.

### `roles` · `role_permissions` — MỚI
```
roles:            code PK · name · is_system bool · sort_order
role_permissions: role_id FK · module_key · tab_key
                  level varchar(10)   -- none | view | edit | approve
                  UNIQUE (role_id, module_key, tab_key)
```
Hiện `users.role` chỉ là chuỗi `admin | user | worker`. Màn Admin › Phân quyền vẽ ma trận vai trò
× tab nhưng chưa có chỗ lưu.

**Quyền hiệu lực = quyền của vai trò, rồi mới đến `user_permissions` ghi đè cho cá nhân.**

---

## 21.5 NHÓM CHẤM CÔNG

### `time_devices` — MỚI
```
code PK · name · serial_no · mac_address · ip_address · location
protocol · last_sync_at · is_active
```
3 máy Ronald Jack, nền ZK `ZMM220_TFT`. Máy số 3 đã ghi nhận: serial `2145222060039`,
MAC `00:17:61:12:0e:f4`, firmware `8.0.4.6-20211110`.

### `attendance_punches` — MỞ RỘNG (bảng đã có)
```
+ employee_id  FK employees NULL   -- phân giải lúc nạp
+ direction    varchar(3) NULL     -- IN | OUT
+ sync_job_id  FK sync_jobs
```
Bảng đang khóa theo **chuỗi** `employee_code`, không có khóa ngoại — mã quẹt lạ sẽ nằm mồ côi
vĩnh viễn. Thêm `employee_id` nullable và một màn Admin "punch chưa khớp người".
**Chỉ ghi thêm, không bao giờ sửa.**

### `attendance_days` — MỞ RỘNG
```
+ work_shift_id FK · leave_code · source varchar(10)   -- machine | manual | import
+ night_hours · sunday_hours · holiday_hours · ot_night_hours
+ segment varchar(10)   -- probation | official
+ is_locked bool · note text
+ edited_by_user_id FK users · edited_at
```

### `leave_requests` — MỚI
```
id · employee_id FK · leave_type_code FK
from_date date · to_date date · from_half bool · to_half bool
total_days numeric(4,2) · reason text · document_path text
status varchar(20)   -- draft | submitted | approved | rejected | cancelled
submitted_at · decided_by_user_id FK users · decided_at · decided_note text
INDEX (status, from_date) · INDEX (employee_id, from_date)
CHECK: không trùng khoảng ngày trên cùng employee_id với đơn đang hiệu lực
```
Thiết kế trước chỉ có **sổ** phép năm mà không có **đơn** — tức là không có gì để duyệt.

### `timesheet_month_details` — MỚI
```
timesheet_month_id FK · category varchar(20) · segment varchar(10)
hours numeric(7,2) · days numeric(5,2)
UNIQUE (timesheet_month_id, category, segment)
```
`category`: `WT`, `OT`, `OT_NIGHT`, `NT30`, `NT45`, `NT60`, `HT`, `ST`, `ABS_<mã nghỉ>`.
Thay cho việc thêm cột mãi mãi.

---

## 21.6 NHÓM TÍNH LƯƠNG

### `payslips` — MỞ RỘNG
```
+ taxable_income          numeric(14,2)
+ family_deduction        numeric(14,2)
+ income_before_tax       numeric(14,2)
+ severance_amount        numeric(14,2)
+ advance_amount          numeric(14,2)
+ al_opening · al_used · al_closing   numeric(5,2)
+ department_name_snapshot varchar(200)
+ team_name_snapshot       varchar(200)
+ closed_at · closed_by_user_id
```
Hai cột `*_snapshot` **cố tình lưu trùng**: chỉ ghi một lần lúc chốt kỳ. Đổi tên tổ năm sau
không được làm đổi phiếu lương đã in năm nay. Trước khi chốt đọc từ khóa ngoại, sau khi chốt đọc
từ ảnh chụp.

### `payslip_components` — MỚI
```
id · payslip_id FK · component_code FK pay_components
segment varchar(10) · seq_no smallint DEFAULT 1
quantity numeric(9,2) · unit varchar(10) · unit_amount numeric(14,2)
amount numeric(14,2) · note text · sort_order int
UNIQUE (payslip_id, component_code, segment, seq_no)
```
**Bắt buộc có `seq_no`.** Một người có thể có hai dòng cùng mã trong một kỳ (truy lĩnh tháng
trước và trừ tiền đồng phục đều là `ADJUST`).

### `annual_leave_ledger` · `annual_leave_entries` — MỚI
```
ledger:  employee_id FK · year · opening_balance · accrued · used · adjusted
         closing_balance · last_accrued_month
         UNIQUE (employee_id, year)
entries: ledger_id FK · entry_date · kind varchar(20)   -- accrual | use | adjust | payout
         days numeric(4,2) · reference · note
```
Phép năm là **sổ có bút toán**, không phải một con số tính lại mỗi lần gọi. Số dư luôn bằng tổng
các dòng, kiểm tra được.

### `employee_bonuses` — MỚI
```
id · employee_id FK · bonus_year · seq_times smallint · bonus_code
base_salary numeric(14,2) · bonus_rate numeric(5,2) · bonus_amount numeric(14,2)
pay_period_id FK · applied_at · reason
UNIQUE (employee_id, bonus_year, seq_times)
```
Nguồn `THR_BONUS`, có hàm `F_GET_BONUS` gọi **thẳng trong tính lương**. Thưởng Tết nhiều đợt.

### `pay_periods` — MỞ RỘNG
```
+ closed_at · closed_by_user_id · reopened_at · reopen_reason
```
Đã chốt thì mọi bảng con chuyển sang **chỉ đọc**.

---

## 21.7 CHỈ MỤC BẮT BUỘC

Quy mô thật: 438 người × 2 lần quẹt × 365 ngày ≈ **320 nghìn dòng punch mỗi năm** và 160 nghìn
dòng công ngày. Đây là chỗ duy nhất cần tính hiệu năng ngay từ đầu.

| Bảng | Chỉ mục | Phục vụ truy vấn |
|------|---------|------------------|
| `attendance_punches` | `(punch_time)`, `(employee_id, punch_time)` | Agent ghi theo khoảng giờ; đối chiếu khiếu nại theo người |
| `attendance_days` | `(work_date, team_id)`, `(employee_id, work_date)` | Bảng công ngày lọc theo ngày + tổ — truy vấn chạy nhiều nhất |
| `payslip_components` | `(payslip_id)`, `(component_code)` | Phiếu lương; báo cáo tổng hợp theo khoản |
| `leave_requests` | `(status, from_date)`, `(employee_id, from_date)` | Hàng đợi duyệt phải mở tức thì |
| `labour_contracts` | `(employee_id, start_date)`, `(end_date)` | Cảnh báo hợp đồng sắp hết hạn |
| `employee_assignments` | `(employee_id, effective_from)` | Tra tổ tại một thời điểm |
| `insurance_declarations` | `(effective_month, status)` | Xuất lô theo tháng |

**Chưa cần partition.** 320 nghìn dòng một năm thì PostgreSQL chạy thoải mái nhiều năm. Chỉ cần
đặt `punch_time` làm cột đầu của chỉ mục và giữ khóa chính kiểu Integer tự tăng như hiện tại —
nếu sau này cần chia theo tháng thì đổi rất rẻ.

---

## 21.8 Tổng kết số lượng

| Loại | Số bảng |
|------|---------|
| Đã có, giữ nguyên | 31 |
| Mở rộng thêm cột | 8 |
| Tạo mới | 28 |
| Tạo mới (Đợt 6 — file 26) | 3 |

---

## 21.9 NHÓM TỰ ĐỘNG HÓA (Đợt 6)

> Chi tiết pipeline và ma trận A0–H: **`26_TU_DONG_HOA_VAN_HANH.md`**. Chỉ tạo khi làm 24§6.x.

| Bảng | Vai trò |
|------|---------|
| `ops_exceptions` | Hàng đợi ngoại lệ — ca lỗi, Δ lương, punch mồ côi |
| `automation_schedules` | Lịch cron (giờ chạy job — không lưu thuật toán) |
| `leave_auto_rules` | Ngưỡng auto-duyệt đơn phép |

---

*Tiếp: `22_QUY_TAC_NGHIEP_VU.md`*
