# Kế hoạch kỹ sư — DJ-HRM (bàn giao Composer 2.5)

**Ngày:** 2026-08-15  
**Kiến trúc sư:** Opus (spec)  
**Kỹ sư code:** Composer 2.5  
**Quy trình:** Mỗi bước = 1 PR/commit riêng → test → ghi `LOI-DA-SUA.txt` → chờ HR/Thiên duyệt → mới sang bước tiếp.

**Đọc trước khi code:**
- Hiến pháp: `HIEN_PHAP/22_QUY_TAC_NGHIEP_VU.md` — **§22.3** (chuyên cần mới), **§22.13** (ca làm việc theo tổ / ca tạp vụ), **§22.14** (chế độ về sớm)
- Quyết định: `HIEN_PHAP/10_QUYET_DINH_CHOT.md` (mục 2026-08-15)
- Schema: `HIEN_PHAP/21_SCHEMA_V2.md` (bảng `employee_wt_regimes`)
- ESC: `.cursor/rules/esc-keyboard.mdc` — overlay mới dùng `useSheetKeyboard` / `useEscLayer`

---

## 0. Quy tắc nghiệp vụ đã chốt (KHÔNG đoán)

### 0.1 Chuyên cần — quy định MỚI (2026-08-15)

| Điều kiện | Hệ quả |
|-----------|--------|
| Đi trễ ≥ **2** lần/tháng | Chuyên cần × **50%** |
| Về sớm ≥ **2** lần/tháng | Chuyên cần × **50%** |
| Đi trễ ≥ **5** lần/tháng | Chuyên cần × **0%** |
| Về sớm ≥ **5** lần/tháng | Chuyên cần × **0%** |
| Có **1 ngày vắng** (mã không miễn) | Chuyên cần × **0%** |

**Không gộp lỗi:** trễ và sớm đếm **riêng**. Trễ 1 + sớm 1 → vẫn 100% (chưa đạt ngưỡng 2).

**Miễn vắng (không tính penalty_absent_days):** `ALE`, `FLE`, `WED`, `TMP`, `OFF` — giữ như cũ.

**Miễn trễ/sớm (không tăng late_count/early_count):** chỉ khi ngày có mã `ALE`/`FLE`/`WED` + nghỉ < 8h + có punch (logic `is_late_early_exempt` hiện có).

**Mất 100% chuyên cần khi nghỉ cả ngày:** mọi mã **không** thuộc miễn vắng — gồm **`PT` (khám thai)**, `MLE`, `SLE`, … HR gán mã phép không trừ bằng tay (`ALE`/`FLE`/`WED`/…) khi cần.

**Không thêm mã quân sự:** HR tự chấm mã miễn — không code mới.

**Nguồn tham số — CÓ HAI NƠI, phải sửa CẢ HAI:**

| Nơi | Ai đọc | Ảnh hưởng tiền? |
|-----|--------|-----------------|
| `policy_packages.payload.attendance_penalties` | **Engine lương** (`timesheet._attendance_penalties` → `engine_allowances.attendance_keep_percent`) | **CÓ** |
| Bảng `attendance_bonus_rules` | Chỉ API hiển thị `/api/policy-rates/attendance-bonus-rules/current` | Không |

> Nếu chỉ sửa bảng `attendance_bonus_rules` → **tiền không đổi**, nhưng màn hình hiển thị lệch với tiền thực tế. Bắt buộc sửa cả hai để không mâu thuẫn.

### 0.2 Chế độ về sớm (Thai sản / Nuôi con) — thủ công trên hồ sơ NV

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| `regime_type` | Có | `PREGNANT` (Thai sản) · `CHILD` (Nuôi con) · null = không |
| `hours_early` | Có | 1 \| 2 \| 3 |
| `date_from` | Có | **≥ hôm nay** khi tạo (không tính lùi) |
| `date_to` | Có | ≥ date_from |

**Mặc định gợi ý UI:** Thai sản → 1h; Nuôi con → 2h (HR sửa được).

**Tab danh sách:** đổi nhãn «Thai sản» → **«Chế độ đặc biệt»** — lọc NV có regime hiệu lực (`date_from ≤ today ≤ date_to`).

**Không** dùng `status=maternity` cho Nuôi con — chỉ bảng regime.

### 0.3 Công thức engine (trong kỳ regime)

```
allowed_out = shift_end − hours_early   # theo ca tổ + regime
if last_out >= allowed_out:
    early_minutes = 0
    worked_hours = min(actual_worked + hours_early, standard_hours)  # bù tối đa 8h
else:
    early_minutes = minutes(allowed_out − last_out)   # chỉ phần vượt
    worked_hours = actual_worked + hours_early        # không bù quá 8h
```

**Ví dụ ca 08–17, Thai sản 1h (ra 16:00):** worked 7h + bù 1h = **8h**, early = 0.  
**Ra 15:00:** worked 6h + bù 1h = **7h**, early = **60 phút** (1 lần về sớm).

**Ngày công (`worked_days`):** vẫn `worked_hours > 0` → +1 (đã có trong `timesheet.py`).

### 0.4 Ca tạp vụ (tổ `Cleaner`)

Tổ: `teams.code = "02"`, `name = "Cleaner"`, thuộc bộ phận **HR & Admin**. Nguồn `apps/api/data/org_structure/teams.csv` dòng `197,02,Cleaner,...` — **`197` là `pk` trong CSV, KHÔNG phải UUID trong DB.** Tra tổ theo `code`, không hard-code id.

| Tham số | Giá trị |
|---------|---------|
| `WorkShift.code` | `CLEANER` |
| Vào ca | 07:00 |
| Nghỉ trưa | 12:00 – 13:00 |
| **Hết ca** (mốc về sớm) | **16:00** |
| 16:00–17:00 | Giờ nghỉ — **không OT** |
| **Mốc OT** | **17:00** (dùng `ot_start` trên ca, **không** dùng `end_time`) |
| Grace OT | 17:15 (policy `ot_split`) |
| OT sổ | 17:00–20:00 Th3+Th5 |

Gán `teams.default_shift_id = CLEANER` cho tổ Cleaner (code `02`).

### 0.5 AI nhắc T−3

Rule Lớp A (`ai_alerts`, 0 token): `date_to − today == 3` → alert + todo card HR.

---

## 1. Thứ tự triển khai (bắt buộc)

| ID | Tên | Phụ thuộc | Rủi ro | Ước |
|----|-----|-----------|--------|-----|
| **A** | Ngưỡng chuyên cần mới (2/2/5/5) | — | Vừa (đụng tiền) | 0.5 ngày |
| **B** | Formatter OT `formatOtHours` | — | Thấp | 0.5 ngày |
| **C** | Ca theo tổ vào engine + seed CLEANER | — | **Cao (lõi)** | 2 ngày |
| **D** | Bảng `employee_wt_regimes` + API + UI hồ sơ + tab | **C** | Vừa | 1.5 ngày |
| **E** | Engine chế độ về sớm trong `calculate_day` | **C**, **D** | **Cao (lõi)** | 1 ngày |
| **F** | AI nhắc T−3 | **D** | Thấp | 0.5 ngày |
| **G** | Cột HR: thâm niên tiền | — | Thấp | 0.5 ngày |
| **H** | Cột HR: phép còn (batch) | — | Vừa (hiệu năng) | 0.5 ngày |
| **I** | Phiếu lương mobile 3 nhóm | — | Thấp | 0.5 ngày |
| **J1** | Bỏ `PT`/`REM` khỏi lọc maternity | — | Thấp | 0.2 ngày |
| **J2** | `rem_days` | **chờ HR** | — | — |

**Một bước / một lần merge.** Không gộp A+B+C.

**Nếu gấp:** A, B, G, I, J1 độc lập hoàn toàn — làm trước để có kết quả sớm. C và E là hai bước lõi, làm chậm và test kỹ.

---

## 2. Chi tiết từng bước

### Bước A — Ngưỡng chuyên cần mới

**Mục tiêu:** Áp dụng trễ **2**/5, sớm **2**/5.

**File sửa:**
1. `apps/api/app/modules/policy/seed_payload.py` — `late_half: 2`, `early_zero: 5` (early_half=2, late_zero=5 giữ)
2. `apps/api/app/modules/policy/seed_rates.py` — `AttendanceBonusRule`: `late_count_half=2`, `early_count_zero=5`
3. `apps/web/src/modules/config/PolicyPackagePage.tsx` — default state `lateHalf=2`, `earlyZero=5`
4. `apps/api/tests/test_policy_payload_v2.py` — cập nhật assert
5. `apps/api/tests/test_policy_rate_tables.py` — cập nhật assert Genus nếu test so khớp 3/2/5/4

**Migration dữ liệu** — `apps/api/alembic/versions/20260815_0050_attendance_penalty_new_thresholds.py`

```python
revision = "20260815_0050"
down_revision = "20260812_0049"   # head hiện tại (allowance_proration)
```

- `UPDATE policy_packages SET payload = jsonb_set(jsonb_set(payload, '{attendance_penalties,late_half}', '2'), '{attendance_penalties,early_zero}', '5') WHERE is_active = true`
- `UPDATE attendance_bonus_rules SET late_count_half = 2, early_count_zero = 5 WHERE effective_to IS NULL`
- `downgrade()` trả về 3 và 4

> **JSON vs JSONB:** test chạy SQLite (`PayloadType = JSON().with_variant(JSONB(), "postgresql")`). Migration `jsonb_set` chỉ chạy Postgres — bọc `if op.get_bind().dialect.name == "postgresql"`, nhánh khác đọc–sửa–ghi bằng Python.

**An toàn kỳ đã chốt:** phiếu lương đã phát hành gắn `payslips.policy_snapshot_id` → **không bị ảnh hưởng**. Nhưng **tính lại kỳ đang mở sẽ dùng ngưỡng mới** — thông báo HR trước khi chạy lại tháng 8.

**Test:**
```powershell
cd apps/api && py -3.12 -m pytest tests/test_policy_payload_v2.py tests/test_policy_rate_tables.py tests/test_attendance_penalty_44.py -q
```

**Kiểm tra tay:** Cấu Hình → Gói chính sách — 4 ô hiện `2 / 2 / 5 / 5`. NV trễ 2 lần trong kỳ → chuyên cần = 50%.

**LOI-DA-SUA:** mã `POL-A001`.

---

### Bước B — Formatter OT

**Mục tiêu:** Một hàm — phút → giờ, tối đa 2 số thập phân, bỏ số 0 thừa, hậu tố `h`.

**File mới:** `apps/web/src/shared/formatOtHours.ts`
```typescript
export function formatOtHours(minutes: number | null | undefined, empty = ""): string {
  if (minutes == null || minutes <= 0) return empty;
  const h = minutes / 60;
  const s = h.toFixed(2).replace(/\.?0+$/, "");
  return `${s}h`;
}
```

**File sửa (thay hiển thị phút/giờ lẻ):**
- `apps/web/src/modules/timekeeping/DailyGridPanel.tsx` — cột OT sổ / OT ngoài
- `apps/web/src/modules/timekeeping/TimekeepingPage.tsx` — `cellMinutes` → `formatOtHours`; monthly `fmtNum` OT → `formatOtHours` hoặc alias giờ
- `apps/web/src/modules/timekeeping/OtExternalPreviewSheet.tsx` — dùng chung (bỏ `fmtHours` local)
- `apps/web/src/modules/report/ReportPage.tsx` — thống nhất suffix `h`
- `apps/web/src/modules/overview/OverviewPage.tsx` — idem

**Test mới:** `apps/web/src/shared/formatOtHours.test.ts` — **đã chạy thử, regex đúng cả số tròn hai chữ số:**

| Phút | Kết quả |
|------|---------|
| 90 | `1.5h` |
| 50 | `0.83h` |
| 45 | `0.75h` |
| 30 | `0.5h` |
| 66 | `1.1h` |
| 120 | `2h` |
| 480 | `8h` |
| 600 | `10h` (không thành `1h`) |
| 1200 | `20h` |
| 0 · null · âm | `""` |

```powershell
cd apps/web && npm test -- formatOtHours && npm run build
```

**LOI-DA-SUA:** mã `OT-B001`.

---

### Bước C — Ca theo tổ vào engine (LÕI — bước khó nhất)

**Mục tiêu:** engine tính theo ca **của tổ NV**, không phải lịch công ty; tách mốc OT (17:00) khỏi mốc hết ca (16:00 với Cleaner).

#### C0 — Hạ tầng ĐÃ CÓ, đừng viết lại

`apps/api/app/modules/attendance/day_enrich.py` đã có:
- `build_shift_cache(db, team_ids, work_dates) -> dict[(team_id, date), shift_code]` — prefetch, không N+1
- `resolve_work_shift_id(db, employee, work_date) -> str` — 1 NV 1 ngày
- `assign_default_shift_to_teams(db)` — gán ADMIN cho tổ chưa có (chỉ khi `default_shift_id IS NULL`, **không** ghi đè CLEANER)

Và **mọi call site đã lấy `shift_id` rồi** — nhưng chỉ để **ghi vào cột** `attendance_days.work_shift_id`, **không** dùng để tính:

| File | Dòng | Hiện tại |
|------|------|----------|
| `service.py` | 161, 178–181 | có `shift_cache`, `shift_id` → chỉ `apply_calc_to_day_row` |
| `day_grid.py` | 245–246, 364–365 | `resolve_work_shift_id` → chỉ ghi cột |
| `review.py` | 238–239 | idem |

> **Đây chính là lỗ hổng LH-1:** `calculate_day()` vẫn nhận `schedule` công ty. Việc của bước C là **nối** shift_id đã có vào `calculate_day`, **không** xây resolver mới.

#### C1 — Hàm chuyển đổi (file mới, nhỏ)

`apps/api/app/modules/attendance/shift_schedule.py`

```python
@dataclass(frozen=True)
class ShiftTiming:
    schedule: Schedule       # dùng cho calculate_day
    ot_start_time: time      # mốc bắt đầu OT ngày thường
    standard_hours: Decimal

def timing_from_shift(shift: WorkShift | None, company: Schedule) -> ShiftTiming:
    """None → trả nguyên lịch công ty (hồi quy 100%)."""
```

Map `WorkShift` → `Schedule`:

| Field Schedule | Nguồn |
|----------------|-------|
| `morning_start` | `shift.start_time` |
| `morning_end` | `shift.lunch_start` |
| `afternoon_start` | `shift.lunch_end` |
| `afternoon_end` | `shift.end_time` ← **16:00 với Cleaner** |
| `grace_late_seconds`, `grace_early_seconds` | **giữ của lịch công ty** (grace không theo ca) |

`ot_start_time` = `shift.ot_start` nếu có, **không** thì `shift.end_time`.

> Nếu `WorkShift` chưa có cột `ot_start` → thêm bằng migration `20260815_0052` (`TIME NULL`). Kiểm tra `models.py` §`class WorkShift` (dòng ~265) trước khi thêm.

**Cache ca:** chỉ vài mã (`ADMIN`, `CLEANER`) → `dict[str, WorkShift]` load 1 query, truyền vào loop.

#### C2 — `engine.py`

- `calculate_day(...)` + `_calc_partial_workday(...)`: thêm kw-only `ot_start: time | None = None`
- Dòng 135 và 264: `ot_qualify_after = combine_vn(work_date, ot_start or schedule.afternoon_end) + timedelta(minutes=split_policy.ot_grace_minutes)`
- `early_deadline` **vẫn** dựa `schedule.afternoon_end` (= 16:00 Cleaner) → bấm ra 16:00 là **bình thường, không về sớm** ✔
- `_shift_worked_hours` (dòng 164–174) không đổi — đã dùng `schedule.afternoon_end`

#### C3 — `ot_split.py`

`split_weekday_ot_minutes(...)`: tham số mốc OT nhận **`ot_start: datetime`** riêng, không suy ra từ `shift_end`. Cửa sổ 17:00–20:00 tính từ `ot_start`, **không** từ `shift_end` → sửa LH-3. Cleaner: 16:00–17:00 rơi ngoài cửa sổ → **0 phút OT** ✔

#### C4 — Seed CLEANER

`seed_shifts.py` — thêm `CLEANER_SHIFT_CODE = "CLEANER"`, idempotent như ADMIN:

```python
WorkShift(code="CLEANER", name="Ca tạp vụ",
          start_time=time(7, 0), end_time=time(16, 0),
          lunch_start=time(12, 0), lunch_end=time(13, 0),
          ot_start=time(17, 0), standard_hours=Decimal("8"))
```

Gán tổ: tra `Team` theo **`code == "02"`** (name `Cleaner`, bộ phận HR & Admin) → `default_shift_id = "CLEANER"`. Idempotent, chỉ gán nếu đang là `ADMIN`/NULL.

> Nguồn `apps/api/data/org_structure/teams.csv`: `197,02,Cleaner,...` — **`197` là `pk` CSV, không phải UUID DB.** Không hard-code id.

#### C5 — Nối 3 call site

Ở mỗi nơi: lấy `shift_id` (đã có) → `shift_map[shift_id]` → `timing_from_shift()` → truyền `schedule=timing.schedule, ot_start=timing.ot_start_time` vào `calculate_day`.

**Giữ `_load_schedule(db)`** cho `is_company_workday` và danh sách ngày làm việc — lịch công ty vẫn quyết định ngày nào là ngày công.

#### C6 — Test

**Mới:** `apps/api/tests/test_shift_cleaner.py`

| Case | Mong đợi |
|------|----------|
| Cleaner, 07:00–16:00, Th2 | `early_minutes=0`, `worked_hours=8`, `ot=0` |
| Cleaner, 07:00–16:30 | `ot_minutes=0` (giờ nghỉ) |
| Cleaner, 07:00–17:30, Th3 | `ot_on_books=30` (tính từ 17:00) |
| Cleaner, 07:00–15:00 | `early_minutes=60` |
| ADMIN, 08:00–17:00 | y như trước (hồi quy) |

```powershell
cd apps/api && py -3.12 -m pytest tests/test_shift_cleaner.py tests/test_attendance_engine.py tests/test_attendance_day_calc_33.py tests/test_work_shifts_24.py tests/test_ot_engine_45.py -q
```

**Rủi ro cao — chạy full suite:** `py -3.12 -m pytest -q`. Bước này sửa lõi, mọi test công/lương đều có thể đỏ.

**LOI-DA-SUA:** mã `SH-C001`.

---

### Bước D — Chế độ về sớm (data + API + UI)

**Migration:** `apps/api/alembic/versions/20260815_0051_employee_wt_regimes.py`

```python
revision = "20260815_0051"
down_revision = "20260815_0050"   # sau bước A
```

> **Chuỗi revision (đừng đụng nhau):** `0049` (head cũ) → `0050` bước A → `0051` bước D → `0052` cột `work_shifts.ot_start` nếu bước C cần.


```sql
CREATE TABLE employee_wt_regimes (
  id UUID PK,
  employee_id UUID FK employees NOT NULL,
  regime_type VARCHAR(20) NOT NULL,  -- PREGNANT | CHILD
  hours_early SMALLINT NOT NULL CHECK (hours_early IN (1,2,3)),
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  note TEXT DEFAULT '',
  created_by_user_id UUID FK users,
  created_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ NULL,
  CHECK (date_to >= date_from)
);
CREATE INDEX ix_wt_regimes_employee_dates ON employee_wt_regimes(employee_id, date_from, date_to);
```

**Model:** `apps/api/app/modules/mdm/models.py` — class `EmployeeWtRegime`

**API:** `apps/api/app/modules/mdm/router.py`
- `GET /api/employees/{id}/wt-regimes`
- `POST /api/employees/{id}/wt-regimes` — validate `date_from >= today`
- `PATCH /api/employees/{id}/wt-regimes/{rid}` — chỉ sửa `date_to`, `hours_early`, `note`
- `POST .../wt-regimes/{rid}/end` — set `date_to=today`, `ended_at=now`

**Service:** `active_wt_regime(db, employee_id, as_of)` → regime or None

**Validate khi POST/PATCH (bắt buộc, trả 400 tiếng Việt):**
1. `date_from >= today` khi **tạo mới** (PATCH được phép giữ `date_from` cũ trong quá khứ)
2. `date_to >= date_from`
3. `hours_early ∈ {1,2,3}`
4. `regime_type ∈ {PREGNANT, CHILD}`
5. **Không chồng kỳ:** từ chối nếu NV đã có bản ghi `ended_at IS NULL` giao khoảng `[date_from, date_to]` — thông báo «NV đã có chế độ hiệu lực đến dd/mm/yyyy — chấm dứt trước khi thêm mới»

**Tính lại công sau khi lưu (QUAN TRỌNG):** sau POST / PATCH / end thành công, gọi `recalculate_days(db, max(date_from, today), min(date_to, today))` cho **riêng NV đó** — nếu không, HR lưu xong mà lưới công không đổi cho tới lần đồng bộ sau. Ngày `is_locked` tự bị bỏ qua (đúng, không mở khóa).

**Tab filter:** `list_employees` — thêm filter `status=special_regime`:
- Query join `employee_wt_regimes` where `date_from <= today <= date_to`
- **Không** dùng `effective_status=maternity` cho Nuôi con

**Frontend:**
- `EmployeesPage.tsx`: `FILTER_META.maternity` → title «Chế độ đặc biệt»; route param giữ `maternity` hoặc đổi `special` (nếu đổi route, cập nhật `HrHomePage.tsx`)
- `EmployeeProfileFields.tsx` hoặc section mới trong `EmployeeProfileCompactFields`: khối «Chế độ về sớm»
- `shared/api.ts` — types + fetch functions

**ESC:** form trong sheet → `useSheetKeyboard` trên container; không `closeOnEsc` trùng.

**Test:**
```powershell
cd apps/api && py -3.12 -m pytest tests/test_wt_regimes_api.py tests/test_employee_status_filter.py -q
cd apps/web && npm test -- escKeyboard && npm run build
```

**Kiểm tra tay:** mở hồ sơ NV → chọn Nuôi con 2h, từ hôm nay đến 31/10 → Lưu → NV xuất hiện tab «Chế độ đặc biệt»; bấm «Chấm dứt» → về tab Chính thức.

**LOI-DA-SUA:** mã `WT-D001`.

---

### Bước E — Engine regime

**File:** `apps/api/app/modules/attendance/engine.py` — sau khi tính `early_minutes` / `worked_hours` thô, gọi `_apply_wt_regime(...)`. Chế độ truyền vào `calculate_day` qua kw-only `wt_hours_early: int | None = None` (None = không có chế độ → không đổi hành vi).

**Prefetch:** trong `recalculate_days`, batch load regimes cho `(employee_ids, date_range)` — **1 query**, không N+1.

**Chỉ áp dụng khi có ĐỦ vào + ra.** Nếu thiếu punch (`_calc_partial_workday`): **không** bù giờ, **không** miễn về sớm — giữ nguyên hành vi cũ. Lý do: thiếu punch là ngoại lệ HR phải xử lý tay, không được che bằng chế độ.

**Không áp dụng ngày nghỉ / lễ** (`is_workday = False`) — nhánh OT ngày nghỉ giữ nguyên.

**Không chạm** `worked_days` trong `timesheet.py` (đã +1 khi `worked_hours > 0`).

**Test:** `apps/api/tests/test_wt_regime_engine.py`
- Thai sản 1h, ca ADMIN, ra 16:00 → `worked_hours=8`, `early_minutes=0`
- Ra 15:00 → `worked_hours=7`, `early_minutes=60`
- Ra 17:00 (không dùng chế độ) → `worked_hours=8` (không thành 9h)
- Nuôi con 2h, ra 15:00 → `worked_hours=8`, `early_minutes=0`
- Ngày trước `date_from` / sau `date_to` → hành vi cũ
- Cleaner (hết ca 16:00) + Thai sản 1h → allowed_out **15:00**
- Chỉ 1 punch → không bù, `worked_hours=0`

```powershell
cd apps/api && py -3.12 -m pytest tests/test_wt_regime_engine.py tests/test_shift_cleaner.py tests/test_attendance_engine.py -q
```

**LOI-DA-SUA:** mã `WT-E001`.

---

### Bước F — AI nhắc T−3

**File:** `apps/api/app/modules/ai/service.py`
```python
def evaluate_wt_regime_reminders(db: Session) -> None:
    # date_to == today + 3 days, regime still active
    create_alert(rule_key="wt_regime_expiring", target_module="hr", ...)
```
Gọi trong `list_mine()` cùng `evaluate_payroll_reminders`.

**File:** `apps/api/app/modules/ai/todos.py` — card «N chế độ sắp hết hạn» → link `/m/hr/employees/maternity`

**`_visible_to`:** thêm `wt_regime_expiring` → admin hoặc `user.has_module("hr")`

**Idempotent:** `source_ref = f"wt_regime:{regime_id}:{date_to}"` — mỗi kỳ nhắc **một lần**; HR gia hạn `date_to` → nhắc mới tự sinh.

**Nội dung mẫu:** `MSNV 5078 — Nuôi con (2h), hết 18/08/2026 (còn 3 ngày). Gia hạn hoặc chấm dứt trên hồ sơ.`

**Test:** `apps/api/tests/test_wt_regime_reminders.py` — `date_to = today+3` → có alert; `today+4` và `today+2` → **không** tạo alert mới; gọi 2 lần → vẫn 1 alert.

> Thêm todo card mới sẽ làm `tests/test_todos_57.py` đếm lệch — cập nhật assert theo key, không theo tổng số.

```powershell
cd apps/api && py -3.12 -m pytest tests/test_wt_regime_reminders.py tests/test_todos_57.py -q
```

**LOI-DA-SUA:** mã `AI-F001`.

---

### Bước G — Cột HR thâm niên tiền

**API:** `EmployeeOut.seniority_amount: Decimal | None` — tính trong `employee_to_out` gọi `seniority_monthly(join_date, today, tiers)` (batch load tiers 1 lần).

**UI:** `EmployeesPage.tsx` FULL view — cột «PC thâm niên» sau `seniority_label`.

**Test:**
```powershell
cd apps/api && py -3.12 -m pytest tests/test_allowances_engine.py tests/test_policy_rate_tables.py tests/test_org_filter_export.py -q
cd apps/web && npm run build
```

**Kiểm tra tay:** NV vào làm 2019 → cột hiện đúng bậc theo `seniority_tiers`; NV mới < 1 năm → trống.

**LOI-DA-SUA:** mã `HR-G001`.

---

### Bước H — Cột HR phép còn lại

**API mới:** `annual_leave_remaining_batch(db, employee_ids, as_of)` trong `annual_leave_ledger.py` — tránh N+1.

**Schema:** `EmployeeOut.annual_leave_remaining: Decimal | None`

**UI:** cột «Phép còn» FULL view.

**Cảnh báo hiệu năng:** `annual_leave_remaining()` hiện gọi `sync_accrual()` **mỗi NV** → 360 NV = 360 vòng. Bản batch phải: (1) load ledger 1 query, (2) load pending ALE 1 query, (3) `sync_accrual` chỉ khi thiếu tháng. Đo thời gian `GET /api/employees` trước/sau — không được chậm hơn **300ms**.

**Test:**
```powershell
cd apps/api && py -3.12 -m pytest tests/test_annual_leave_ledger_47.py tests/test_nghiem_thu_47.py tests/test_payroll_ui_49.py -q
```

**LOI-DA-SUA:** mã `HR-H001`.

---

### Bước I — Phiếu lương mobile 3 nhóm

**Tham chiếu:** `apps/api/app/modules/payroll/payslip_detail.py` (work / allowance / deduction).

**Sửa:** `apps/api/app/modules/worker/payslips.py` + `WorkerPayslipDetailOut` + `WorkerPayslipPage.tsx` — 3 accordion thay 2.

**Không đổi số tiền** — chỉ nhóm lại cách hiển thị. Tổng `net` phải khớp tuyệt đối với bản HR.

**Test:**
```powershell
cd apps/api && py -3.12 -m pytest tests/test_worker_payslips.py -q
cd apps/web && npm run build
```

**LOI-DA-SUA:** mã `WK-I001`.

---

### Bước J — Tab maternity + rem_days

**J1 — làm ngay:** `employment_status.py` — `MATERNITY_LEAVE_CODES = frozenset({"MLE", "MC"})` — **bỏ `PT`, `REM`**.

Lý do: `PT` (khám thai) là nghỉ **nửa/một ngày lẻ**, không phải đang nghỉ thai sản → không được đẩy NV ra khỏi tab Chính thức. `REM` không nằm trong 14 mã thật (§22.6).

```powershell
cd apps/api && py -3.12 -m pytest tests/test_employee_status_filter.py -q
```

**J2 — CHỜ HR XÁC NHẬN, chưa code:** định nghĩa `rem_days`.

Hiện `timesheet.py` (~dòng 312–320) chỉ cộng `ALE` vào `al_days`, `rem_days` **luôn = 0**. Trước khi sửa cần HR trả lời:

1. `rem_days` = ngày nghỉ **BHXH chi trả** (`PT`, `MLE`, `MC`, `SLE`, `SCH`) — đúng không?
2. Nguồn đếm: `timesheet_adjustments` (HR nhập tay) hay `attendance_days.leave_code` (từ đơn phép) — hay **cả hai, chống đếm trùng**?
3. Cột này in trên bảng lương gửi kế toán không?

> **Không đoán.** Sai `rem_days` → sai số liệu BHXH. Hỏi HR rồi mới viết code.

**LOI-DA-SUA:** mã `HR-J001` (chỉ J1).

---

## 3. Checklist trước khi đóng mỗi bước

- [ ] Chỉ file trong phạm vi bước — **không** refactor kèm
- [ ] pytest / vitest pass (lệnh trong bước)
- [ ] Chạy full suite API: `cd apps/api && py -3.12 -m pytest -q` — **không** được đỏ thêm test nào
- [ ] `npm run build` nếu sửa web
- [ ] Nếu sửa overlay → `npm test -- escKeyboard`
- [ ] Nếu có migration → `alembic upgrade head` **và** `alembic downgrade -1` rồi `upgrade head` lại
- [ ] Kiểm tra tay theo mục «Kiểm tra tay» của bước
- [ ] Thêm mục `Thien-Admin/LOI-DA-SUA.txt` (triệu chứng → nguyên nhân → cách xử lý → test)
- [ ] **Không** commit/push trừ khi user yêu cầu

**Nếu bước sai sau khi merge:** `git revert` commit của bước đó; migration có `downgrade()` đầy đủ nên rollback DB được. Không có bước nào xoá dữ liệu cũ.

---

## 4. Rủi ro đã biết (đừng tái phát)

| ID | Mô tả | Xử ở bước |
|----|--------|-----------|
| LH-1 | `resolve_work_shift_id` đã chạy ở mọi call site nhưng chỉ **ghi cột**; `calculate_day` vẫn nhận lịch công ty | **C** |
| LH-3 | `ot_split.py` hard-code cửa sổ 17:00–20:00 theo `shift_end` → Cleaner hết ca 16:00 sẽ tính OT giờ nghỉ | **C** |
| LH-4 | `worked_days` đã +1 khi `worked_hours > 0` — chế độ **không** cần sửa `timesheet.py` | — |
| LH-7 | Không tính lùi ngày — `date_from ≥ today` ép ở API, không chỉ ở UI | **D** |
| LH-8 | OT hiển thị lẫn lộn phút/giờ giữa các trang | **B** |
| LH-9 | `annual_leave_remaining()` N+1 (gọi `sync_accrual` mỗi NV) | **H** |
| LH-15 | Ngưỡng chuyên cần có **2 nguồn** (payload JSON tính tiền · bảng chỉ hiển thị) — sửa lệch là mâu thuẫn số | **A** |

---

## 4b. Việc CHỜ HR xác nhận (không code trước)

| Việc | Câu hỏi |
|------|---------|
| `rem_days` (bước J2) | Gồm mã nào? Đếm từ đơn phép hay HR nhập tay? |
| Tính lại tháng 8 sau khi đổi ngưỡng | HR đồng ý chuyên cần tháng 8 tính theo ngưỡng mới 2/5? |
| Nhãn tab | «Chế độ đặc biệt» hay giữ «Thai sản»? |

---

## 5. Prompt gợi ý cho Composer 2.5 (copy từng bước)

```
Đọc Thien-Admin/KE-HOACH-KY-SU-2026-08-15.md — thực hiện BƯỚC [X] only.
Tuân thủ HIEN_PHAP/22 §22.3, §22.13, §22.14. Không sửa bước khác.
Chạy test trong spec. Ghi LOI-DA-SUA.txt. Báo cáo kết quả, không commit.
Nếu phát hiện spec thiếu/sai: DỪNG và báo, không tự quyết.
```

---

*Bản spec **v1.1** — 2026-08-15 — Kiến trúc sư Opus*

**Sửa so với v1.0 (soát lại lần 2):**
- Bước C viết lại: hạ tầng `build_shift_cache` / `resolve_work_shift_id` **đã có** trong `day_enrich.py` — nối vào `calculate_day`, không xây resolver mới
- Chuỗi revision Alembic: `0049` → A `0050` → D `0051` → C `0052` (v1.0 để hai bước cùng `0050`, sẽ xung đột)
- Sửa tên test không tồn tại: `test_annual_leave_ledger_47.py`, `test_allowances_engine.py` (không có `test_seniority.py`)
- Thêm cảnh báo LH-15: ngưỡng chuyên cần có 2 nguồn, chỉ payload JSON mới đụng tiền
- Thêm: phiếu lương đã chốt an toàn nhờ `policy_snapshot_id`, nhưng kỳ đang mở sẽ đổi số
- Thêm validate chồng kỳ + **gọi lại `recalculate_days` sau khi lưu chế độ** (thiếu bước này HR lưu xong không thấy gì đổi)
- Bước J tách J1 (làm ngay) / J2 (chờ HR xác nhận `rem_days`)
- Bỏ hard-code `197` — tra Tổ theo `teams.code = "02"`
- Kiểm chứng `formatOtHours` bằng node: 600 phút → `10h`, không bị cắt thành `1h`
- Hiến pháp: chuyển ca tạp vụ + chế độ về sớm ra **§22.13 / §22.14** (trước đó nằm sai dưới §22.6 «14 loại nghỉ»)
