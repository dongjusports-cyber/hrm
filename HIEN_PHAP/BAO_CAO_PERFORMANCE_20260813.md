# BÁO CÁO PERFORMANCE AUDIT — P0

**Ngày:** 2026-08-13  
**Phạm vi:** Chức năng **"Lấy công từ máy"** (Sync Pipeline) và **"Load danh sách công"** (Daily Grid Rendering)  
**Bối cảnh:** ~350 nhân viên, sync mất ~10 phút — lỗi kiến trúc, không phải lỗi phần cứng đơn lẻ.  
**Mục tiêu tối ưu:** Sync 350 NV trong **< 1 phút**; load/render lưới ngày công mượt, không treo UI.

> **Lưu ý:** Báo cáo này chỉ phân tích và đề xuất — **không chỉnh sửa mã nguồn**.

---

## Tóm tắt điều hành (Executive Summary)

| Hạng mục | Kết luận chính | Mức độ |
|----------|----------------|--------|
| **Sync Pipeline** | Kiến trúc pull-based, đồng bộ end-to-end; không có background job; ingest từng punch; recalc/rebuild chạy inline trong HTTP request | **P0** |
| **Agent poll** | Mặc định poll mỗi **15 phút** → HR chờ tới 15 phút trước khi Agent bắt đầu | **P0** |
| **Job lifecycle** | Job HR tạo (`requested` → `running`) **khác** job ingest hoàn thành → UI poll sai job, timeout 10 phút dù sync đã xong | **P0** |
| **Frontend Grid** | AG Grid **đã có row virtualization** (DOM ~15–25 dòng); nhưng **350 dòng load full vào memory**, reload API sau mỗi cell edit, search không debounce | **P0/P1** |

**Ước tính thời gian 10 phút hiện tại:**

```
0–15 phút   Chờ Agent poll (SYNC_INTERVAL_MINUTES=15)
+ 5–120s    ODBC đọc SQL Mitapro (tùy khoảng ngày)
+ 30–120s+  API ingest (per-punch transaction × N punch)
+ 5–60s+    recalculate_days + rebuild_timesheets (inline)
+ 0–10 phút UI poll timeout nếu job lifecycle lỗi
─────────────────────────────────────────────────────
≈ 2–15+ phút (thường cảm nhận ~10 phút)
```

---

## PHẦN 1: SYNC PIPELINE (Backend / Service / Agent)

### 1.1. Sơ đồ luồng đồng bộ hiện tại

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  HR Web — MitaproSyncPanel / syncWithProgress.ts                            │
│  "Đồng bộ ngay" → POST /api/attendance/sync-now                             │
│  Tạo SyncJob status="requested" (job A)                                     │
│  Poll mỗi 2.5s: GET sync-jobs + integration/status                        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ (chờ Agent — mặc định tới 15 phút)
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DJ Agent (Windows) — apps/agent/dj_agent/                                  │
│  run_forever(): mỗi SYNC_INTERVAL_MINUTES (default 15):                     │
│    1. GET  /api/integrations/mitapro/pending                              │
│    2. Vòng lặp TUẦN TỰ từng pending job:                                   │
│         POST claim → job A status="running"                                 │
│         ODBC SELECT CheckInOut (1 query batch, KHÔNG loop từng NV)          │
│         POST /api/integrations/mitapro/push (1 body chứa toàn bộ punches)   │
│    3. LUÔN chạy thêm run_once() scheduled (trùng lặp SQL+push)            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  API — apps/api/app/modules/integration/service.py                          │
│  ingest_punches():                                                          │
│    • Tạo SyncJob MỚI (job B) — KHÁC job A HR đang poll                    │
│    • FOR EACH punch: nested transaction + INSERT + flush                    │
│    • commit                                                                 │
│    • recalculate_days() — INLINE, blocking                                   │
│    • rebuild_timesheets() mỗi tháng bị ảnh hưởng — INLINE                   │
│  Trả response → Agent httpx timeout 60s                                    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                ▼
  PostgreSQL: sync_jobs, attendance_punches, attendance_days, timesheet_month

Nguồn dữ liệu (KHÔNG gọi trực tiếp máy chấm công):
  [Máy chấm công] → [Mitapro app] → [SQL Server MITACOSQL.CheckInOut]
                                           ↑ ODBC SELECT (Agent only)
```

### 1.2. Có đang loop tuần tự từng người không?

| Tầng | Loop từng NV? | Chi tiết |
|------|---------------|----------|
| Agent SQL read | **Không** | 1 `SELECT` cho cả khoảng thời gian (`sql_reader.py:13-22`, `96-120`) |
| Agent HTTP push | **Không** | 1 POST chứa toàn bộ `punches[]` (`pusher.py:25-51`) |
| API ingest | **Không** (tệ hơn: **từng punch**) | `for p in body.punches` (`service.py:88-126`) |
| API recalculate_days | **Có** (từng employee-day) | `for (code, wd), times in grouped.items()` (`attendance/service.py:143-161`) |
| API rebuild_timesheets | **Có** (từng NV) | `for emp_id, emp in emp_map.items()` (`timesheet.py:250-338`) |
| Agent pending jobs | **Có** (từng job) | `for job in pending` (`sync_loop.py:65-84`) |

**Kết luận:** Không có vòng lặp mạng từng NV tới máy chấm công, nhưng API xử lý **tuần tự từng punch** và **tuần tự từng employee-day / từng NV** trong recalc/rebuild — đây là nguyên nhân chính khi scale 350 NV.

### 1.3. I/O Blocking

| Vị trí | Loại I/O | Hành vi blocking |
|--------|----------|------------------|
| `sql_reader.py:97-120` | ODBC / SQL Server | `pyodbc.connect(timeout=30)`, `conn.timeout=60`, `fetchall()` — block thread Agent |
| `pusher.py:38-51` | HTTP Agent→API | `httpx.Client.post(timeout=60)` — chờ toàn bộ ingest+recalc+rebuild |
| `pusher.py:54-83` | HTTP | Mỗi request tạo `httpx.Client` mới — không connection pool |
| `sync_loop.py:129` | Sleep | `time.sleep(interval * 60)` — block giữa các chu kỳ |
| `integration/router.py:37-44` | FastAPI sync handler | `def mitapro_push` (không `async def`) — block uvicorn worker |
| `syncWithProgress.ts:127` | Frontend poll | `await sleep(2500)` mỗi vòng |

**Không có:** async I/O, background job queue, WebSocket wake Agent, gọi SDK máy chấm công trực tiếp.

### 1.4. Danh sách nghẽn cổ chai — Sync (có file:dòng)

#### P0 — Nghiêm trọng

| ID | File:Dòng | Mô tả | Ước tính impact |
|----|-----------|-------|-----------------|
| **S-P0-1** | `apps/api/app/modules/integration/service.py:88-126` | **Ingest từng punch với nested transaction.** Mỗi punch: `db.begin_nested()` → `db.add()` → `db.flush()` → catch `IntegrityError`. 5k–30k punch = O(n) round-trip DB. | 10k punch: **~30–120s+** chỉ riêng ingest |
| **S-P0-2** | `apps/api/app/modules/integration/service.py:162-177` | **Recalc + rebuild timesheet INLINE** trong `ingest_punches`, block HTTP response Agent. | Thêm **5–60s+** sau ingest |
| **S-P0-3** | `apps/agent/dj_agent/pusher.py:38-39` | **HTTP timeout 60s** trên push. Toàn bộ ingest+recalc+rebuild phải xong trong 60s. | Re-sync tháng / backfill lớn → **timeout, sync thất bại** |
| **S-P0-4** | `apps/agent/dj_agent/config.py:26` + `sync_loop.py:112-129` | **`sync_interval_minutes: int = 15`** — Agent chỉ thức dậy mỗi 15 phút. UI cảnh báo rõ (`syncWithProgress.ts:75-78`). | **Tới 15 phút** trước khi Agent bắt đầu — chiếm phần lớn "10 phút" cảm nhận |
| **S-P0-5** | `service.py:207-220` + `269-280` + `66-77` + `syncWithProgress.ts:100-105` | **Job lifecycle tách đôi.** HR tạo job A (`requested`). Agent claim → A=`running`. `ingest_punches` tạo **job B mới** hoàn thành. Frontend poll job A → **không bao giờ thấy terminal status**. | UI **timeout 10 phút** (`syncWithProgress.ts:94,130-133`) dù sync đã thành công |
| **S-P0-6** | `apps/agent/dj_agent/sync_loop.py:119-122` | Sau `process_pending()`, **luôn chạy thêm** `run_once(reason="schedule")` — duplicate ODBC + HTTP push cùng cửa sổ. | **2×** tải SQL + API mỗi chu kỳ khi vừa manual sync |

#### P1 — Cao

| ID | File:Dòng | Mô tả | Ước tính impact |
|----|-----------|-------|-----------------|
| **S-P1-1** | `apps/api/app/modules/attendance/service.py:143-161` | **N+1 trong recalculate_days:** mỗi `(employee_code, work_date)` query `AttendanceDay` + `resolve_work_shift_id`. | ~2 query × employee-days (350×30 = **21k query**/tháng) |
| **S-P1-2** | `day_enrich.py:24-28` → `shifts_service.py:90-97` | **`get_effective_shift` gọi `assign_default_shift_to_teams(db)` mỗi lần** — seed + query all teams. | Nhân lên theo số employee-day trong recalc |
| **S-P1-3** | `apps/api/app/modules/attendance/timesheet.py:250-338` | **`rebuild_timesheets` loop toàn bộ NV payroll-eligible** dù `recalc_days=False`. | **5–30s** mỗi lần sync tháng |
| **S-P1-4** | `timesheet.py:295` | **`_attendance_penalties(db)` trong vòng lặp từng NV** — query PolicyPackage lặp lại. | N query giống nhau mỗi rebuild |
| **S-P1-5** | `pusher.py:38,54,64,75` | **Tạo `httpx.Client` mới mỗi request** — không reuse connection/TLS. | ~100–500ms overhead/chu kỳ trên WAN |
| **S-P1-6** | `sync_loop.py:65-84` | Pending jobs xử lý **tuần tự** — không parallel. | N job range-sync xếp hàng tuyến tính |
| **S-P1-7** | `sql_reader.py:96-120` | ODBC sync blocking, `fetchall()` load toàn bộ vào RAM. | Giây–phút + memory spike với cửa sổ lớn |
| **S-P1-8** | `syncWithProgress.ts:103-105` | Mỗi poll 2.5s: `fetchSyncJobs(20)` + `fetchIntegrationStatus()` + **`findJob()` gọi thêm `fetchSyncJobs(15)`**. | **~3 API calls / 2.5s** ≈ 1440 calls trong 10 phút |
| **S-P1-9** | `integration/router.py:37-44` | Handler đồng bộ `def` — block uvicorn worker (prod thường `--workers 2`). | 1 worker bị chiếm phút — HR request khác chậm |
| **S-P1-10** | `service.py:283-332` | `integration_status` chạy **5+ query DB** mỗi lần poll. | Tải DB trong cửa sổ poll 10 phút |

### 1.5. Đánh giá kiến trúc hiện tại

| Khả năng | Có? | Ghi chú |
|----------|-----|---------|
| Background Jobs (Celery/RQ/ARQ) | **Không** | Toàn bộ trong HTTP request |
| Redis cache sync state | **Không** | Redis client có nhưng chỉ dùng health check |
| Bulk INSERT / batch ingest | **Không** | Per-row nested transaction |
| Agent push notification | **Không** | Chỉ poll `/mitapro/pending` |
| HTTP connection pooling (Agent) | **Không** | New client mỗi call |
| Job status coherence | **Lỗi** | Job claimed ≠ job ingest (S-P0-5) |
| Chunking / pagination punch | **Không** | Full window 1 SQL query + 1 HTTP body |

### 1.6. Đề xuất kiến trúc tối ưu — Sync

#### Mô hình mục tiêu (< 1 phút cho 350 NV)

```
HR click "Đồng bộ ngay"
    │
    ▼
API: tạo SyncJob → publish Redis Pub/Sub "agent:wake" (hoặc giảm poll xuống 30s)
    │
    ▼
Agent nhận lệnh < 5s → ODBC SELECT (1 batch) → POST /push (chunk 5k nếu cần)
    │
    ▼
API: trả 202 Accepted ngay (< 1s) — KHÔNG recalc inline
    │
    ▼
Background Worker (Celery/RQ):
    1. Bulk INSERT punches (ON CONFLICT DO NOTHING)
    2. recalculate_days (bulk prefetch AttendanceDay)
    3. rebuild_timesheets (chỉ NV bị ảnh hưởng)
    4. Cập nhật CÙNG SyncJob HR đang poll
    │
    ▼
Frontend poll job status từ Redis/DB — thấy 100% trong < 60s
```

#### Ưu tiên triển khai (ROI cao → thấp)

| # | Giải pháp | File cần sửa | Impact ước tính |
|---|-----------|--------------|-----------------|
| 1 | **Background job** cho ingest+recalc; API trả 202 | `service.py`, `router.py` | Agent không timeout; worker free < 1s |
| 2 | **Bulk INSERT** thay per-punch transaction | `service.py:88-126` | Ingest 10k punch: **120s → 2–5s** (20–50×) |
| 3 | **Sửa job lifecycle** — dùng 1 job duy nhất | `service.py:66-77`, `claim_pending_request` | UI poll đúng, hết false timeout |
| 4 | **Giảm poll Agent** xuống 1–2 phút HOẶC Redis wake | `config.py:26`, Agent mới | Latency HR: **15 phút → < 30s** |
| 5 | **Skip scheduled run_once** khi pending vừa chạy | `sync_loop.py:119-122` | −50% ODBC+API mỗi chu kỳ |
| 6 | **Bulk prefetch** trong recalculate_days | `attendance/service.py:143-161` | −21k query → ~10 query |
| 7 | **Bỏ `assign_default_shift_to_teams` khỏi hot path** | `shifts_service.py:96-97` | Giảm commit/query trong recalc |
| 8 | **Cache `build_employee_resolve_maps`** Redis TTL 5 phút | `punch_resolver.py` | −1 full employee scan/ingest |
| 9 | **Reuse httpx.Client** trong ApiPusher | `pusher.py` | −TLS handshake/chu kỳ |
| 10 | **Chunk push** 5k punches/request + timeout động | `sql_reader.py`, `pusher.py` | Tránh OOM + timeout |

#### Bảng ước tính end-to-end (350 NV, ~700 punch/ngày)

| Kịch bản | Hiện tại | Sau P0 fix | Sau tối ưu đầy đủ |
|----------|----------|------------|-------------------|
| Sync hàng ngày | 0–15 phút chờ + 15–90s API | < 2s enqueue + 1–2 phút background | **< 30s** end-to-end |
| Re-sync 1 tháng (~21k punch) | **Timeout / thất bại** (60s) | 2–5s enqueue + ~30s background | **< 45s** |
| HR "Đồng bộ ngay" cảm nhận | **0–15 phút** + có thể false timeout | 1–2 phút | **< 30s** |
| DB queries/sync | ~30k+ | ~500 | ~50–200 |

---

## PHẦN 2: RENDER BẢNG DANH SÁCH CÔNG (Frontend Grid)

### 2.1. Sơ đồ luồng render

```
TimekeepingPage mount
    │
    ▼
reload(): fetchTimesheets, leaves, pay period
    │
    ▼
mainView === "daily" → DailyGridPanel mount
    │
    ▼
load(): GET /api/attendance/days/grid
    │   Backend list_days_grid(): load ALL active employees (không pagination)
    │   apps/api/.../day_grid.py:104-165
    │
    ▼
setRows(~350 AttendanceDayGridRow) — full payload vào React state
    │
    ▼
useMemo filteredRows (searchQuery từ parent — mỗi keystroke)
    │   DailyGridPanel.tsx:108-116
    │   TimekeepingPage.tsx:730-734, 891
    │
    ▼
useMemo summary → onSummaryChange → parent setDailySummary (re-render cả page)
    │   DailyGridPanel.tsx:118-126
    │   TimekeepingPage.tsx:316-318
    │
    ▼
AgGridReact rowData={filteredRows}
    │   DailyGridPanel.tsx:456-494
    │
    ▼
AG Grid 33 — row virtualization (DOM ~15-25 dòng visible)
    Container fixed height: global.css:3752-3765
```

### 2.2. Trạng thái Virtualization

| Lớp | Trạng thái | Bằng chứng |
|-----|------------|------------|
| `react-window` / `react-virtuoso` | **Không** | Không có trong `apps/web/package.json:12-18` |
| AG Grid row virtualization | **Có (mặc định)** | Không `domLayout="autoHeight"`; container cố định `global.css:3752-3765`; `animateRows={false}` (`DailyGridPanel.tsx:463`) |
| AG Grid column virtualization | **Có (mặc định)** | ~14 cột |
| Data virtualization / server pagination | **Không** | Full ~350 row JSON (`DailyGridPanel.tsx:87`, `day_grid.py:104-165`) |
| Server-side row model | **Không** | Client-side only |

**Kết luận:** DOM **không** render 350×14 cell cùng lúc (AG Grid chỉ render ~15–25 dòng). Tuy nhiên **toàn bộ 350 dòng nằm trong memory**, được filter/sort/diff mỗi khi state thay đổi — đây vẫn là bottleneck khi tương tác.

### 2.3. Danh sách nghẽn cổ chai — Render (có file:dòng)

#### P0 — Nghiêm trọng

| ID | File:Dòng | Mô tả | Impact |
|----|-----------|-------|--------|
| **R-P0-1** | `DailyGridPanel.tsx:267-310` (`onCellChanged` → `await load()` dòng 305-306, 309) | **Reload toàn bộ API sau mỗi cell edit.** Mỗi sửa 1 ô = fetch lại 350 dòng + refresh grid. | Latency tương tác tệ nhất — cảm giác "treo" khi sửa công |
| **R-P0-2** | `TimekeepingPage.tsx:730-734,891` + `DailyGridPanel.tsx:108-116` | **Search không debounce** — mỗi keystroke: parent re-render → `filteredRows` recompute → `rowData` thay đổi → AG Grid update full dataset. | Gõ tìm kiếm gây jank trên 350 dòng |
| **R-P0-3** | `day_grid.py:104-165` + `DailyGridPanel.tsx:82-87` | **API trả full danh sách NV, không pagination.** ~350 object × 25+ field mỗi lần load/refresh. | Initial load + mỗi refresh chậm (network + parse JSON) |
| **R-P0-4** | `DailyGridPanel.tsx:124-126` + `TimekeepingPage.tsx:316-318` | **`onSummaryChange` bubble lên parent** → `setDailySummary` → re-render toàn bộ `TimekeepingPage` + `DailyGridPanel`. | Re-render cascade mỗi khi filter thay đổi |

#### P1 — Cao

| ID | File:Dòng | Mô tả | Impact |
|----|-----------|-------|--------|
| **R-P1-1** | `TimekeepingPage.tsx:308-314` + `DailyGridPanel.tsx:259` | `pickFromDaily` deps `[rows, pickEmployee]` → `cols` useMemo rebuild khi timesheet reload | AG Grid column refresh không cần thiết |
| **R-P1-2** | `DailyGridPanel.tsx:459,468-475,477-481,483-487,488-493` | Inline props (`getRowId`, `onGridReady`, `getRowClass`, `defaultColDef`) tạo mới mỗi render | Grid reconciliation thừa |
| **R-P1-3** | `DailyGridPanel.tsx:483-487` | `getRowClass` chạy per visible row mỗi refresh | CPU khi scroll/refresh |
| **R-P1-4** | `DailyGridPanel.tsx:134-157` | 3 cột pinned trái (checkbox, MSNV, tên) | AG Grid render pinned + center — ~3× cell work khi scroll |
| **R-P1-5** | `DailyGridPanel.tsx:352-388` | Paste handler: loop sequential API + `load()` cuối | Bulk paste = N round-trip + 1 full reload |
| **R-P1-6** | `TimekeepingPage.tsx:907` | Monthly grid `animateRows` bật | Animation overhead (tab tháng) |

### 2.4. Computation trong render path

AG Grid gọi `valueGetter` / `valueFormatter` / `getRowClass` khi hiển thị, sort, refresh — **không phải React render** nhưng vẫn là hot path.

| Tính toán | File:Dòng | Chi phí | Ghi chú |
|-----------|-----------|---------|---------|
| `formatTimeHHMM` qua `hhmm()` | `DailyGridPanel.tsx:19-21,188,205` → `formatDate.ts:65-74` | **Cao** | `new Date()` + `toLocaleTimeString("vi-VN")` mỗi lần đọc cell Vào/Ra |
| `formatOrgName` regex | `DailyGridPanel.tsx:164-167,174-175` → `formatOrg.ts:27-31` | Trung bình | Regex strip dept/team mỗi cell read |
| `formatLeaveLabel` linear search | `DailyGridPanel.tsx:249` → `formatLeave.ts:7-16` | Trung bình | `leaves.find()` O(n) mỗi cell nghỉ |
| `compareHhmmEmptyFirst` sort | `DailyGridPanel.tsx:184,201` → `agGridVi.ts:18-33` | Trung bình | Chạy khi sort 350 dòng |
| `filteredRows` filter | `DailyGridPanel.tsx:108-116` | Trung bình | O(350) mỗi keystroke |
| `summary` scan | `DailyGridPanel.tsx:118-122` | Trung bình | O(350) thứ hai mỗi filter change |

**Chưa precompute server-side:** giờ hiển thị, tên bộ phận đã strip, label nghỉ — tất cả tính lúc đọc cell.

### 2.5. Đề xuất kiến trúc tối ưu — Render

#### Mô hình mục tiêu

```
API /days/grid
    │
    ├─ Option A: Server pagination (50/page) + needs_action filter default
    ├─ Option B: Trả thêm *_display fields (first_in_display, dept_display, leave_display)
    │
    ▼
DailyGridPanel
    ├─ Search debounce 250ms HOẶC AG Grid quickFilterText (không đổi rowData)
    ├─ Cell edit → applyTransaction (patch 1 row) — KHÔNG load() full
    ├─ Summary render trong DailyGridPanel (không bubble parent)
    ├─ useCallback/useMemo ổn định cho AG Grid props
    │
    ▼
AG Grid (giữ nguyên — đã virtualize DOM)
    rowBuffer={5}, animateRows={false} ✓
```

#### Ưu tiên triển khai

| # | Giải pháp | File | Impact |
|---|-----------|------|--------|
| 1 | **Optimistic/local update** sau cell save thay `load()` | `DailyGridPanel.tsx:305-306` | Loại bỏ bottleneck tương tác #1 |
| 2 | **Debounce search** hoặc AG Grid Quick Filter | `TimekeepingPage.tsx:891`, `DailyGridPanel.tsx:108-116` | Hết jank khi gõ |
| 3 | **Summary local** — không `onSummaryChange` lên parent | `DailyGridPanel.tsx:124-126` | Giảm re-render cascade |
| 4 | **Precompute display fields** lúc fetch | `DailyGridPanel.tsx:87`, `day_grid.py` | Bỏ valueGetter nóng |
| 5 | **Map leave code → label** một lần | `formatLeave.ts` | O(1) lookup thay find |
| 6 | **Stabilize callbacks** (`useCallback` getRowId, getRowClass) | `DailyGridPanel.tsx:459-493` | Ít grid reconciliation |
| 7 | **Stabilize pickFromDaily** (dùng ref thay deps `rows`) | `TimekeepingPage.tsx:308-314` | cols không rebuild khi reload timesheet |
| 8 | **Server pagination** hoặc lazy load | `day_grid.py:93-165` | Giảm payload initial |
| 9 | **KHÔNG thêm react-window/virtuoso** | — | AG Grid đã virtualize; thêm layer sẽ conflict |

#### Phụ — Tab tháng & detail sheet

| ID | File:Dòng | Vấn đề |
|----|-----------|--------|
| R-P2-1 | `TimekeepingPage.tsx:907` | `animateRows` bật trên monthly grid |
| R-P2-2 | `TimekeepingPage.tsx:387-401` | React `cellRenderer` button mỗi visible row |
| R-P2-3 | `TimekeepingPage.tsx:566-621` | Calendar detail: `<table>` không virtualize 28–31 ngày |
| R-P2-4 | `TimekeepingPage.tsx:122-172` | `buildCalendar` recompute toàn bộ ngày |

---

## PHẦN 3: BẢNG TỔNG HỢP P0

| # | Hạng mục | File:Dòng chính | Nguyên nhân gốc |
|---|----------|-----------------|-----------------|
| 1 | Agent poll 15 phút | `config.py:26`, `sync_loop.py:129` | Pull model, không wake |
| 2 | Ingest per-punch | `service.py:88-126` | Không bulk INSERT |
| 3 | Recalc inline | `service.py:162-177` | Không background job |
| 4 | HTTP timeout 60s | `pusher.py:38` | Sync path quá dài |
| 5 | Job lifecycle lỗi | `service.py:66-77` vs `269-280` | 2 job ID khác nhau |
| 6 | Duplicate scheduled sync | `sync_loop.py:119-122` | Luôn chạy run_once sau pending |
| 7 | Full reload sau edit | `DailyGridPanel.tsx:305-306` | Không optimistic update |
| 8 | Search không debounce | `TimekeepingPage.tsx:730-734` | rowData churn |

---

## PHẦN 4: LỘ TRÌNH ĐỀ XUẤT (KHÔNG CODE — CHỈ KIẾN TRÚC)

### Sprint 1 — Quick wins (không đổi kiến trúc lớn)

1. Giảm `SYNC_INTERVAL_MINUTES` xuống **1–2** trên máy Agent production
2. Sửa job lifecycle: ingest cập nhật **cùng** job HR poll
3. Frontend: debounce search; bỏ `load()` sau cell edit → `applyTransaction`
4. Skip `run_once` scheduled khi pending vừa xử lý xong

**Kỳ vọng:** 10 phút → **2–4 phút** (chủ yếu giảm chờ Agent + UI timeout)

### Sprint 2 — Backend throughput

1. Bulk INSERT punches (`INSERT ... ON CONFLICT DO NOTHING`)
2. Background worker cho `recalculate_days` + `rebuild_timesheets`
3. API push trả **202 Accepted** ngay
4. Bulk prefetch trong recalc; bỏ `assign_default_shift_to_teams` khỏi hot path

**Kỳ vọng:** Sync processing **< 60s** cho 350 NV/ngày

### Sprint 3 — Scale & UX

1. Redis: agent wake channel + job progress cache
2. Chunk push 5k punches
3. Server pagination grid + precomputed display fields
4. Connection pooling Agent HTTP

**Kỳ vọng:** End-to-end **< 30s**; grid load/edit mượt

---

## PHỤ LỤC: Chỉ mục file quan trọng

| Thành phần | Đường dẫn |
|------------|-----------|
| Agent sync loop | `apps/agent/dj_agent/sync_loop.py` |
| Agent HTTP client | `apps/agent/dj_agent/pusher.py` |
| Agent SQL reader | `apps/agent/dj_agent/sql_reader.py` |
| Agent config | `apps/agent/dj_agent/config.py` |
| API ingest | `apps/api/app/modules/integration/service.py` |
| API routes | `apps/api/app/modules/integration/router.py` |
| Day recalc | `apps/api/app/modules/attendance/service.py` |
| Timesheet rebuild | `apps/api/app/modules/attendance/timesheet.py` |
| Shift N+1 | `apps/api/app/modules/attendance/shifts_service.py` |
| Grid API | `apps/api/app/modules/attendance/day_grid.py` |
| Frontend progress | `apps/web/src/modules/timekeeping/syncWithProgress.ts` |
| Frontend sync panel | `apps/web/src/modules/timekeeping/MitaproSyncPanel.tsx` |
| Frontend daily grid | `apps/web/src/modules/timekeeping/DailyGridPanel.tsx` |
| Frontend page shell | `apps/web/src/modules/timekeeping/TimekeepingPage.tsx` |
| AG Grid locale/sort | `apps/web/src/shared/agGridVi.ts` |
| Time format hot path | `apps/web/src/shared/formatDate.ts` |

---

*Báo cáo được tạo bởi Performance Audit — chỉ phân tích, không thay đổi mã nguồn ứng dụng.*
