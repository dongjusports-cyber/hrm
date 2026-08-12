# 07 — Schema Database (PostgreSQL)

> Kiểu tiền: `NUMERIC(18,2)` hoặc `NUMERIC(18,4)` cho bước trung gian.  
> Mọi bảng nghiệp vụ nên có `created_at`, `updated_at`.  
> Soft-delete khi cần: `deleted_at`.

## 7.1 Core & Auth

```sql
users (
  id UUID PK,
  username TEXT UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,              -- admin | user | worker
  employee_id UUID NULL,           -- link NV nếu là worker hoặc staff gắn MSNV
  is_active BOOLEAN DEFAULT TRUE,
  must_change_password BOOLEAN DEFAULT FALSE
)

user_module_grants (
  user_id UUID FK,
  module_key TEXT,                 -- overview, hr, ...
  PRIMARY KEY (user_id, module_key)
  -- CHECK: admin bypass; user max 7; config chỉ admin
)

user_permissions (
  user_id UUID FK,
  permission_key TEXT,             -- ai_query
  PRIMARY KEY (user_id, permission_key)
)

audit_logs (
  id BIGSERIAL PK,
  actor_user_id UUID,
  action TEXT,
  entity_type TEXT,
  entity_id TEXT,
  before_json JSONB,
  after_json JSONB,
  ip TEXT,
  created_at TIMESTAMPTZ
)
```

## 7.2 MDM — Nhân sự

```sql
departments (
  id UUID PK,
  code TEXT UNIQUE,                -- SW1, B01...
  name TEXT,
  category TEXT,                   -- direct | prod_indirect | admin_indirect
  mitapro_names TEXT[]             -- alias mapping
)

employees (
  id UUID PK,
  employee_code TEXT UNIQUE,       -- MSNV
  full_name TEXT,
  gender TEXT,
  id_number TEXT,                  -- CCCD
  bank_account TEXT NULL,
  pay_channel TEXT,                -- ATM | CASH
  department_id UUID FK,
  position_title TEXT,
  join_date DATE,
  contract_signed_at DATE NULL,    -- ngày ký HĐ chính thức
  probation_salary NUMERIC(18,2),
  contract_salary NUMERIC(18,2),
  si_base_override NUMERIC(18,2) NULL, -- ghi đè Lương đóng BH cho ca ngoại lệ; mặc định NULL = TỰ TÍNH
  -- Lương đóng BH tự tính = contract_salary + Σ phụ cấp có include_in_si_base=TRUE (giá trị đầy đủ)
  si_enrolled BOOLEAN DEFAULT TRUE,
  union_fee_override NUMERIC(18,2) NULL,
  status TEXT DEFAULT 'active',    -- active | probation | resigned | suspended
  resign_date DATE NULL,           -- ngày nghỉ việc (dùng cho turnover + ngừng trả lương)
  phone TEXT NULL
)

employee_allowance_assignments (
  employee_id UUID FK,
  allowance_type_id UUID FK,
  amount NUMERIC(18,2) NULL,      -- override
  meta JSONB                       -- số con, bậc...
)

employee_children (
  employee_id UUID FK,
  full_name TEXT,
  birth_date DATE
)
```

## 7.3 Policy & Calendar

```sql
portal_tabs (
  key TEXT PK,
  title TEXT,
  icon TEXT,
  sort_order INT,
  is_enabled BOOLEAN,
  is_system BOOLEAN                -- config luôn system
)

policy_packages (
  id UUID PK,
  name TEXT,                       -- "Mùa cao điểm T10"
  effective_from DATE,
  effective_to DATE NULL,
  is_active BOOLEAN,
  payload JSONB NOT NULL           -- toàn bộ hệ số
  -- xác nhận 3 lần khi save: ghi confirm_log
)

policy_snapshots (
  id UUID PK,
  pay_period_id UUID FK,
  package_id UUID,
  payload JSONB NOT NULL,          -- đóng băng lúc tính lương
  created_at TIMESTAMPTZ
)

allowance_types (
  id UUID PK,
  code TEXT UNIQUE,
  name TEXT,
  proration TEXT,
  include_in_si_base BOOLEAN,       -- cộng vào base khấu trừ BH
  include_in_ot_base BOOLEAN,       -- cộng vào base tính OT (chuyên cần=TRUE ở đây nhưng FALSE ở si_base)
  default_amount NUMERIC(18,2),
  rules JSONB                      -- seniority tiers, etc.
)

leave_types (
  code TEXT PK,
  name TEXT,
  paid_by_company BOOLEAN,
  counts_as_unauthorized BOOLEAN,
  affects_attendance_bonus JSONB
)

holidays (
  date DATE PK,
  name TEXT
)

work_week_rules (
  id SMALLINT PK DEFAULT 1,
  work_weekdays INT[],             -- 1=Mon..7=Sun
  morning_start TIME,
  morning_end TIME,
  afternoon_start TIME,
  afternoon_end TIME,
  grace_late_minutes INT DEFAULT 0
)

pay_periods (
  id UUID PK,
  year INT,
  month INT,
  date_from DATE,
  date_to DATE,
  official_work_days NUMERIC(6,2),
  salary_divisor NUMERIC(6,2),
  status TEXT,                     -- open | calculating | published | locked
  policy_snapshot_id UUID NULL,
  UNIQUE(year, month)
)
```

### Ví dụ `policy_packages.payload` (JSON)

```json
{
  "ot_rates": {"weekday": 1.5, "weekend": 2.0, "holiday": 3.0, "night_addon": 0.3, "ot_night_extra": 0.2},
  "si_rates": {"bhxh": 0.08, "bhyt": 0.015, "bhtn": 0.01},
  "union_fee_default": 44100,
  "attendance_bonus_monthly": 230000,
  "attendance_penalties": {
    "late": [{"min": 3, "max": 4, "keep_percent": 50}, {"min": 5, "max": 999, "keep_percent": 0}],
    "early_or_absent_group": [
      {"absent_days": 1, "or_early_times": 2, "keep_percent": 50},
      {"absent_days_gte": 2, "keep_percent": 0}
    ],
    "combine_late_early": false,
    "exempt_leave_codes": ["AL", "MARRIAGE", "FUNERAL", "HEALTHCHECK"]
  },
  "divisor_rule": {"when_official_eq": 27, "use_divisor": 26, "else": "official"},
  "payslip_confirm_days": 7,
  "transport_monthly_default": 760000
}
```

## 7.4 Attendance & Integration

```sql
sync_jobs (
  id UUID PK,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  status TEXT,
  records_in INT,
  message TEXT
)

attendance_punches (
  id BIGSERIAL PK,
  employee_code TEXT,
  punch_time TIMESTAMPTZ,
  source TEXT,                     -- mitapro
  raw JSONB
)

attendance_days (
  id UUID PK,
  employee_id UUID FK,
  work_date DATE,
  first_in TIMESTAMPTZ,
  last_out TIMESTAMPTZ,
  worked_hours NUMERIC(6,2),
  late_minutes INT,
  early_minutes INT,
  ot_minutes INT,
  ot_type TEXT,
  UNIQUE(employee_id, work_date)
)

timesheet_months (
  id UUID PK,
  pay_period_id UUID FK,
  employee_id UUID FK,
  worked_days NUMERIC(8,4),
  al_days NUMERIC(8,4),
  rem_days NUMERIC(8,4),
  late_count INT,
  early_count INT,
  ot_hours_weekday NUMERIC(8,2),
  ot_hours_weekend NUMERIC(8,2),
  ot_hours_holiday NUMERIC(8,2),
  UNIQUE(pay_period_id, employee_id)
)
```

## 7.5 Payroll & Payslip & Dispute

```sql
payroll_runs (
  id UUID PK,
  pay_period_id UUID FK,
  status TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  employee_count INT
)

payslips (
  id UUID PK,
  pay_period_id UUID FK,
  employee_id UUID FK,
  policy_snapshot_id UUID FK,
  wd_salary NUMERIC(18,2),
  allowance_total NUMERIC(18,2),
  ot_pay NUMERIC(18,2),
  other_adjustments NUMERIC(18,2) DEFAULT 0,  -- Re-Pay/truy lĩnh/bù trừ (1 danh mục gộp)
  gross NUMERIC(18,2),
  bhxh NUMERIC(18,2),
  bhyt NUMERIC(18,2),
  bhtn NUMERIC(18,2),
  union_fee NUMERIC(18,2),
  other_deductions NUMERIC(18,2),
  pit_amount NUMERIC(18,2) DEFAULT 0,
  net NUMERIC(18,2),
  status TEXT,                     -- draft|published|confirmed|disputed|resolved|expired
  confirmed_at TIMESTAMPTZ NULL,
  confirm_deadline DATE NULL,
  lines JSONB,                     -- chi tiết từng khoản
  UNIQUE(pay_period_id, employee_id)
)

payslip_adjustments (            -- khoản cộng/trừ bất thường nhập tay (gộp Re-Pay + tạm ứng…)
  id UUID PK,
  pay_period_id UUID FK,
  employee_id UUID FK,
  kind TEXT,                       -- addon | deduction
  reason TEXT,                     -- "Truy lĩnh T9", "Tạm ứng"...
  amount NUMERIC(18,2),
  created_by UUID,
  created_at TIMESTAMPTZ
)

disputes (
  id UUID PK,
  code TEXT UNIQUE,                -- K001
  payslip_id UUID FK,
  employee_id UUID FK,
  reason_code TEXT,
  description TEXT,
  status TEXT,                     -- open|ai_reviewed|hr_pending|closed
  ai_summary TEXT NULL,
  assigned_user_id UUID NULL,
  created_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ
)

ai_jobs (
  id UUID PK,
  user_id UUID,
  kind TEXT,                       -- dispute_review | chat
  prompt TEXT,
  response TEXT,
  tokens_in INT,
  tokens_out INT,
  created_at TIMESTAMPTZ
)

ai_alerts (
  id UUID PK,
  rule_key TEXT,
  title TEXT,
  body TEXT,
  target_module TEXT,
  is_read BOOLEAN DEFAULT FALSE,
  user_id UUID NULL,               -- null = broadcast theo quyền
  created_at TIMESTAMPTZ
)
```

## 7.6 Index khuyến nghị

- `employees(employee_code)`, `employees(department_id)`
- `attendance_days(work_date)`, `attendance_days(employee_id, work_date)`
- `payslips(pay_period_id, status)`
- `disputes(status, created_at)`

*Tiếp: `08_MODULE_API_HOP_DONG.md`*
