# 26 — TỰ ĐỘNG HÓA VẬN HÀNH

> Đọc cùng file **20**. Chi tiết nghiệp vụ vẫn ở **22**; màn hình Hub ở **23§23.8**; lộ trình code ở **24§Đợt 6**.
> Phiên bản **2.1** · Ngày **2026-08-13** · Chủ sở hữu: **Nguyễn Thanh Thiện**
> Trạng thái: **ĐÃ CHỐT Ý TƯỞNG** — triển khai code **sau v1.0** (trừ hạng mục 24§6.x ghi rõ “trong v1.0”)

---

## 26.0 Mục tiêu

**HR không đi 30 màn — HR vận hành một pipeline tháng + một hàng đợi ngoại lệ.**

| Máy làm (tự động) | Người làm (bắt buộc) |
|-------------------|----------------------|
| Đồng bộ Mitapro, gom punch, tính công | Ký / chấm dứt HĐ, sa thải, kỷ luật |
| Tích lũy phép năm, đề xuất BHXH | Đổi **chính sách tiền** (xác nhận 3 bước — 10§) |
| Tính lương **nháp** theo policy snapshot | **Chốt kỳ** sau khi so số |
| Nhắc việc, cảnh báo, đối chiếu GenusSuite | Giải quyết **khiếu nại** (AI chỉ gợi ý — 05§) |
| Auto-duyệt đơn phép **trong ngưỡng** | Ngoại lệ REM, OT đặc biệt, lệch lớn |

Không vi phạm **N8** (20§20.2): Admin chỉ chứa **số, tỷ lệ, ngày, danh mục** — thuật toán và thứ tự
bước nằm trong mã nguồn. Bảng cấu hình auto chỉ lưu **ngưỡng bật/tắt**, không lưu flow.

---

## 26.1 Kiến trúc — Pipeline + Hàng đợi ngoại lệ

```
[Mitapro Agent] ──► punch ──► tính công ngày ──► tổng hợp tháng
                                    │                    │
                                    ▼                    ▼
                            ops_exceptions ◄────── (rule phát hiện lỗi)
                                    │
                                    ▼
                         Operations Hub (1 màn HR)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Sửa ngoại lệ    Cổng 1-click    Báo cáo / todo
              (F2, duyệt)     chốt / publish
```

### Ba lớp chạy nền

| Lớp | Hành vi | Ví dụ |
|-----|---------|-------|
| **L0 — Silent** | Chạy nền, không hỏi | Sync Agent, dedupe punch, accrual phép tháng |
| **L1 — Auto + todo** | Làm xong, tạo thẻ việc (05§ Lớp A, **0 token**) | “29 ca lỗi”, “347 phiếu nháp — xem Δ” |
| **L2 — Cổng HR** | Tính/chuẩn bị xong, **chờ 1 click** | Chốt công tháng, phát hành lương, xuất lô BHXH |

**Gemini (05§ Lớp B)** chỉ khi user có `ai_query` **bấm Gửi** — không tự sửa DB, không auto trên Worker.

---

## 26.2 Bảng mức tự động A0 → H

Chủ chốt mức mặc định go-live; Admin chỉ **bật/tắt** từng rule (không sửa thuật toán).

| Mức | Tên | Ý nghĩa |
|-----|-----|---------|
| **A0** | Full auto | Không hỏi HR |
| **A1** | Auto + báo | Làm xong + thẻ todo / alert |
| **A2** | Auto nếu 0 exception | Chạy khi `ops_exceptions` = 0 cho loại đó |
| **A3** | Luôn 1 click HR | Chuẩn bị xong, HR duyệt cổng |
| **H** | Human only | Không auto |

### Ma trận mặc định (có thể siết sau 2 kỳ song song GenusSuite)

| Việc | Mức | Ghi chú |
|------|-----|---------|
| Agent sync Mitapro | **A0** | 04§ — đã chốt |
| Map punch + dedupe 60s | **A0** | 24§3.2 |
| Tính công ngày / tháng | **A0** → **A1** nếu có lỗi | Lỗi → exception |
| Tích lũy phép năm (ledger) | **A0** | 24§4.7 |
| Đề xuất BHXH tháng | **A1** | HR tick + xuất — 24§5.5 |
| HĐ sắp hết 60 ngày | **A1** | Todo đã có — mở rộng Hub |
| Auto-duyệt đơn phép (trong ngưỡng) | **A2** | 26§26.4 |
| Tính lương nháp | **A1** | Job nền — 11§ |
| Phát hành phiếu lương | **A3** | Không auto lần đầu go-live |
| Chốt kỳ lương | **A3** | Có thể A2 sau 2 kỳ khớp GenusSuite |
| Đổi policy tiền | **H** | 3-step confirm |
| Khiếu nại / kỷ luật / sa thải | **H** | |

---

## 26.3 Pipeline tháng (mẫu — Admin chỉnh giờ cron)

| Thời điểm | Job tự động | HR (nếu có) |
|-----------|-------------|-------------|
| Hằng ngày 02:00 | Sync hôm qua + tính công ngày | — |
| Cuối ngày | Rollup cảnh báo ca lỗi → todo | Sửa ngoại lệ trong ngày (tuỳ) |
| Ngày 28–31 | Tổng hợp `timesheet_month_details` | — |
| Ngày 1 02:00 | Accrual phép tháng mới | — |
| Ngày 1 03:00 | `calculate_period` **nháp** (nếu công tháng trước `ready`) | — |
| Ngày 1 sáng | Todo: “Xem Δ lương”, “BHXH tháng T” | Hub |
| Ngày 3–5 | — | **Phát hành** phiếu (A3) |
| Ngày 8 | Nhắc phiếu chưa xác nhận (rule có sẵn) | — |
| Trước ngày 15 | Todo `period_lock_overdue` | **Chốt kỳ** (A3) |

Ngày cụ thể là **seed**; lưu trong bảng cấu hình lịch (chỉ số ngày/giờ, không sửa công thức).

---

## 26.4 Tự động theo module

### Chấm công (~90% A0/A1)

- Punch → `attendance_days` → `timesheet_month_details`: **A0**
- Chip “Chỉ hiện cần xử lý” feed **ops_exceptions** type `attendance_gap`
- **Chốt bảng công tháng:** A2 nếu `exception_count=0`, else A3

### Nghỉ phép (~70% → 85%)

- Công nhân xin nghỉ (24§5.8) → `leave_requests`
- **Auto-duyệt (A2)** khi đồng thời:
  - `leave_code` ∈ danh sách Admin cho phép auto
  - `total_days` ≤ ngưỡng (seed: 5)
  - Không vượt số dư phép (`annual_leave_ledger`)
  - Không chồng đơn khác
- Sau duyệt (auto hoặc tay): job gán mã nghỉ lên `attendance_days` — **A0**

### Lương (~80% A1, cổng A3)

- Engine: chỉ đọc snapshot + công — **không đổi** (22§)
- `calculate_period`: job ARQ/RQ — trả `job_id` + progress (11§)
- Flag \|Δ net\| ≥ ngưỡng (seed 500.000) → exception + tô đỏ lưới (đã có UI)
- **Publish / lock:** A3 go-live; xem xét A2 sau nghiệm thu

### BHXH & hồ sơ

- `insurance_declarations` đề xuất tăng/giảm/đổi lương: **A1**
- Giảm trừ gia cảnh: tính từ `employee_family_members` — **A0**
- Gợi ý ký HĐ tiếp (`suggested_*` API): **A1** — HR ký **H**

### Operations Hub (màn trung tâm)

Gom từ `compute_todo_cards` + `ops_exceptions` + `ai_alerts` (05§ Lớp A):

| Thẻ | Nguồn | Link |
|-----|-------|------|
| Ca công lỗi hôm nay | exception | Chấm công đã lọc |
| Đơn phép chờ tay | leave queue | Duyệt nghỉ |
| HĐ hết hạn 60 ngày | todo | Hợp đồng |
| BHXH chưa nộp | todo | Bảo hiểm |
| Agent sync lỗi | alert | Đồng bộ / runbook 15§ |
| Δ lương bất thường | exception | Bảng lương |

UI: **23§23.8** — Trang chủ theo vai trò; code ở **24§5.7** + **24§6.3**.

---

## 26.5 Công nghệ (bổ sung V1 — không đổi stack)

| Thành phần | Vai trò | Ghi chú |
|------------|---------|---------|
| **Redis + ARQ hoặc RQ** | Cron + job lương/công/export | **Không** coi là message broker nặng — 20§20.1b |
| **`ops_exceptions`** (bảng mới) | type, entity, reason, resolved_at | Feed Hub |
| **`automation_schedules`** (bảng mới) | cron expr, job_key, enabled | Chỉ lịch, không logic |
| **`leave_auto_rules`** (bảng mới) | ngưỡng auto-duyệt | N8 — không flow graph |
| Rule Lớp A (`ai_alerts`, `/ai/todos`) | Mở rộng rule_key | 0 token — 05§ |
| FastAPI + PostgreSQL + Agent | Giữ nguyên | 06§ |

**Cấm:** BPMN engine, microservices, AI tự ghi DB, auto đổi policy.

---

## 26.6 Schema gợi ý (bổ sung 21 — triển khai Đợt 6)

### `ops_exceptions`

```
id · exception_type varchar(40) · entity_type · entity_id
severity varchar(10)   -- info | warn | block
message text · detail jsonb
created_at · resolved_at · resolved_by_user_id FK
INDEX (exception_type, resolved_at) · INDEX (created_at)
```

### `automation_schedules`

```
job_key PK · cron_expr · enabled bool · last_run_at · last_status
note text   -- ví dụ: "daily_attendance 02:00"
```

### `leave_auto_rules`

```
effective_from date · max_days_auto smallint · allowed_leave_codes text[]
require_zero_balance bool · enabled bool
```

Chi tiết cột đầy đủ khi làm migration — grep 21.1 trước khi tạo.

---

## 26.7 Nghiệm thu tự động hóa (số, không “xong rồi”)

| # | Tiêu chí |
|---|----------|
| 1 | Tắt HR 3 ngày liên tiếp (mô phỏng): sync vẫn chạy, công ngày vẫn cập nhật |
| 2 | Tháng 0 exception chấm công → **Chốt công** 1 click (hoặc A2 auto) |
| 3 | 10 đơn phép 1 ngày, đủ phép → auto-duyệt; 1 đơn 10 ngày → vào queue tay |
| 4 | Ngày 1: lương nháp có sẵn; HR **không** bấm “Tính lương” thủ công |
| 5 | Publish vẫn cần click; audit_log ghi user + thời điểm |
| 6 | Mọi job fail → alert tiếng Việt + không auto-lock tháng |
| 7 | Regression MSNV **1519** kỳ 07/2026 vẫn **9.682.398** sau bật pipeline |

---

## 26.8 Việc không bao giờ tự động

- Đổi `policy_packages` / bảng rate có tiền (trừ seed ban đầu)
- Xác nhận / từ chối khiếu nại thay HR
- Sa thải, kỷ luật, quyết định lương đặc biệt ngoài policy
- Ghi đè `attendance_punches` (N5)
- Sửa phiếu kỳ **đã chốt** (N3)
- Patch production / deploy (chỉ khi Chủ yêu cầu — 20§20.4)

---

## 26.9 Liên kết tài liệu

| File | Liên quan |
|------|-----------|
| `24_LO_TRINH_5_DOT.md` §Đợt 6 | Hạng mục code triển khai |
| `05_AI_GEMINI.md` | Lớp A todo/alert; Lớp B read-only |
| `04_CHAM_CONG_AGENT.md` | Agent A0 |
| `11_YEU_CAU_PHI_CHUC_NANG.md` | Job nền, timeout |
| `15_RUNBOOK_KHONG_IT.md` | Khi auto fail |
| `V1_0_DINH_NGHIA.md` | Đóng v1.0 trước khi bật A2 publish/lock |
| `Update_UI_UX` (báo cáo tư vấn) | UI Hub / shadcn sau v1.0 |

---

*Quay lại `20_HIEN_PHAP_V2_QUY_TRINH.md` · Lộ trình code: `24§Đợt 6`*
