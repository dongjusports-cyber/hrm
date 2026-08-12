# 08 — Module Map, API, Hợp đồng báo cáo phiên

## 8.1 Module → Code mapping

| Module key | Backend path | Frontend path | Việc chính |
|------------|--------------|---------------|------------|
| `core` | `modules/core` | `shared/auth` | Login JWT, RBAC guard |
| `config` | `modules/config` | `modules/config` | Tabs, users, 3-step confirm |
| `mdm` | `modules/mdm` | `modules/hr` | NV, bộ phận |
| `policy` | `modules/policy` | `modules/config/*` | Policy packages |
| `calendar` | `modules/calendar` | `modules/config/calendar` | Lễ, mẫu số |
| `integration` | `modules/integration` | `modules/timekeeping` + agent | Mitapro ingest |
| `attendance` | `modules/attendance` | `modules/timekeeping` | Công, trễ/sớm |
| `payroll` | `modules/payroll` | `modules/payroll` | Tính lương |
| `payslip` | `modules/payslip` | `worker/*` + payroll detail | Phiếu |
| `dispute` | `modules/dispute` | `modules/dispute` | Khiếu nại |
| `report` | `modules/report` | `modules/report` | KPI |
| `ai` | `modules/ai` | `shared/AiFab` | Badge + Gemini |
| `insurance` | `modules/insurance` | `modules/insurance` | BH |

## 8.2 API surface (tối thiểu)

### Auth
- `POST /api/auth/login` `{username, password}` → tokens + grants
- `POST /api/auth/change-password`
- `GET /api/auth/me`

### Portal metadata
- `GET /api/portal/tabs` — 8 ô (kèm `allowed: bool` theo user)
- `PUT /api/config/tabs` — Admin only

### MDM / HR
- `GET/POST/PUT /api/employees`
- `POST /api/employees/import`
- `GET/PUT /api/departments`

### Attendance
- `POST /api/integrations/mitapro/push` — Agent token
- `POST /api/attendance/sync-now`
- `GET /api/attendance/timesheets?period=`
- `GET /api/integrations/status`

### Payroll
- `POST /api/payroll/periods/{id}/calculate`
- `POST /api/payroll/periods/{id}/publish`
- `POST /api/payroll/periods/{id}/lock`
- `GET /api/payroll/payslips?period=`
- `GET /api/payroll/payslips/{id}`

### Worker
- `POST /api/worker/login` — MSNV + password
- `GET /api/worker/payslips`
- `POST /api/worker/payslips/{id}/confirm`
- `POST /api/worker/payslips/{id}/dispute`

### Dispute / AI
- `GET /api/disputes`
- `POST /api/disputes/{id}/assign`
- `POST /api/ai/alerts` (internal)
- `GET /api/ai/alerts/mine`
- `POST /api/ai/query` — requires `ai_query` — body `{message, dispute_id?}`

### Config / Policy
- `GET/PUT /api/policies/packages/{id}` — 3-step: header `X-Confirm-Step: 1|2|3`
- `GET /api/calendar/divisor?year=&month=`

## 8.3 Guard chuẩn

```
@require_module("payroll")
@require_permission("ai_query")   # khi cần
@require_admin()                  # config
```

Click FE ô không quyền: **không gọi API** — chỉ toast/popup tiếng Việt.  
Nếu gọi API thẳng: trả 403 với message COSMOS AI.

## 8.4 Hợp đồng báo cáo chuyển giao phiên (BẮT BUỘC)

Mỗi khi AI kết thúc phiên làm việc, báo cáo theo mẫu:

```markdown
## Báo cáo phiên — DJ HRM
- **Ngày / phiên:** ...
- **Mục tiêu phiên:** ...
- **File Hiến pháp đã neo:** (liệt kê)
- **Module đụng vào:** ...
- **File đã tạo/sửa:**
  - path — thay đổi ngắn
- **Migration DB:** có/không (tên revision)
- **Test đã chạy:** ...
- **Đối chiếu Excel:** có/không (kỳ nào, lệch?)
- **Rủi ro / nợ kỹ thuật:** ...
- **Bước phiên sau (1–3 việc):** ...
- **Snapshot trạng thái:** build chạy được? (yes/no)
```

## 8.5 Contextual Anchoring — neo regression

Luôn giữ fixture:

- 3–5 NV từ Oct/2025: `1514`, `1643`, `5290`, `5321`, `1732`
- Kỳ `2025-10`, divisor `26`, so `wd_salary` / `net`

*Tiếp: `09_LO_TRINH_PHIEN.md`*
