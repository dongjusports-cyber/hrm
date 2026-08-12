# 06 — Công nghệ & Kiến trúc

## 6.1 Stack BẮT BUỘC (theo `Công nghệ sử dụng.docx` + quyết định Cloud)

| Lớp | Công nghệ | Ghi chú |
|-----|-----------|---------|
| Backend | **Python + FastAPI** | Modular routers/services |
| ORM | **SQLAlchemy 2.x** | Alembic migrations |
| Frontend | **React (Vite) + TypeScript** | SPA |
| Bảng dữ liệu | **AG-Grid** | Bảng lương / nhân sự |
| DB | **PostgreSQL** | JSONB cho metadata/policy |
| Tiền tệ | **`decimal.Decimal`** | Bắt buộc |
| Container | **Docker Compose** | Local Win10 + Cloud |
| Cache/Queue | Redis + worker (ARQ/Celery/RQ) | Sync & payroll jobs |
| Auth | JWT + RBAC | bcrypt passwords |
| AI | Google **Gemini Pro** API | |
| Reverse proxy | Nginx (cloud) / uvicorn local | |
| Agent | Python hoặc Node trên Windows | Đọc SQL Server Mitapro |

## 6.2 Môi trường triển khai

### Phase Local (trước)
- Windows 10 Pro, i3, RAM 16GB
- Docker Desktop
- Không cần preview fancy — cần **file code + docker-compose** chạy được

### Phase Cloud
- VPS Việt Nam (4 vCPU / 8GB khuyến nghị)
- Domain + SSL
- Backup pg_dump hàng ngày

## 6.3 Kiến trúc tổng thể

```
┌──────────────────────────────────────────────────────┐
│  React Vite (Web Portal 8 ô + /worker PWA)           │
└─────────────────────────┬────────────────────────────┘
                          │ HTTPS / JSON
┌─────────────────────────▼────────────────────────────┐
│  FastAPI Modular Monolith                            │
│  ├── core (auth, rbac, audit)                        │
│  ├── mdm (employees, orgs)                           │
│  ├── policy (metadata engine)                        │
│  ├── calendar                                        │
│  ├── integration (mitapro ingest)                    │
│  ├── attendance                                      │
│  ├── payroll (formula engine)                        │
│  ├── payslip + dispute                               │
│  ├── report                                          │
│  ├── ai (gemini + rules)                             │
│  └── config (tabs metadata, users)                   │
└───────┬─────────────────────┬────────────────────────┘
        │                     │
   PostgreSQL              Redis/Queue
        ▲
        │ HTTPS push
┌───────┴────────┐
│ DJ Agent    │  (máy Mitapro)
│ read-only SQL  │
└────────────────┘
```

## 6.4 Metadata-driven — các “bảng cấu hình sống”

| Metadata | Khả năng |
|----------|----------|
| `portal_tabs` | Thêm / xóa / đổi tên / đổi thứ tự / ẩn ô Lv1 |
| `policy_packages` | Gói mùa (chuyên cần, phạt, OT…) |
| `allowance_types` | Catalog phụ cấp |
| `leave_types` | AL/REM/… |
| `formula_defs` | Biểu thức hoặc step engine versioned |
| `ai_alert_rules` | Ngưỡng nhắc việc |

## 6.5 Cấu trúc thư mục repo đề xuất

```
dj-hrm/
├── apps/
│   ├── api/                 # FastAPI
│   │   ├── app/main.py
│   │   ├── app/modules/
│   │   │   ├── core/
│   │   │   ├── mdm/
│   │   │   ├── policy/
│   │   │   ├── calendar/
│   │   │   ├── integration/
│   │   │   ├── attendance/
│   │   │   ├── payroll/
│   │   │   ├── payslip/
│   │   │   ├── dispute/
│   │   │   ├── report/
│   │   │   ├── ai/
│   │   │   └── config/
│   │   ├── alembic/
│   │   └── tests/
│   ├── web/                 # React Vite
│   │   ├── src/portal/      # Lv1 8 ô
│   │   ├── src/modules/     # Lv2+ theo tab
│   │   ├── src/worker/      # PWA công nhân
│   │   └── src/shared/
│   └── agent/               # Mitapro sync agent (Windows)
├── docker-compose.yml
├── docs/ → symlink hoặc copy HIEN_PHAP/
└── README.md
```

## 6.6 Quy tắc code

1. Một module = router + service + schemas + models (không cross-import lung tung)
2. Payroll service chỉ nhận `PolicySnapshot` + dữ liệu công — không đọc “magic number”
3. Mọi endpoint lỗi: `{"detail": "tiếng Việt..."}`  
4. Test regression: fixture tháng 10/2025 (ít nhất 5 NV mẫu + 1 full import sau)
5. Không float tiền
6. Mọi thay đổi policy tiền: require 3-step confirm API flag từ FE

## 6.6a Luật tổ chức file — “Chia nhỏ để trị” có điều kiện (theo Chủ)

> Ý Chủ: *Những file có thể tách mang lại tối ưu thì tách; file dù lớn mà tách ra là tệ thì bắt buộc không tách. Chia nhỏ trên nền tảng khoa học lợi ích — không phải cứ thấy file lớn là tách.*

### Mục tiêu
- **Cô lập lỗi:** hư chấm công → sửa `attendance`, không đụng `payroll` trừ khi contract API đổi.
- **AI / phiên sau** mở đúng vài file liên quan task, không lạc trong rừng file vụn.
- **Chủ không IT** vẫn hiểu: “module Lương”, “module Chấm công”.

### Được tách (lợi ích khoa học)

| Tách gì | Vì sao có lợi |
|---------|----------------|
| Theo **module nghiệp vụ** (`payroll/`, `attendance/`, `ai/`) | Hư cái nào sửa cái đó |
| Trong module: `router.py` · `service.py` · `schemas.py` · `models.py` | Ranh giới HTTP / logic / DB rõ |
| `formula_engine.py` vs `payslip_publisher.py` | Tính toán ≠ phát hành phiếu |
| `web/src/worker/` vs `web/src/modules/` | Hai đối tượng user khác nhau |
| `agent/` riêng khỏi `api/` | Chạy Windows on-prem, deploy khác cloud |
| Test theo module `tests/modules/payroll/` | Regression không chạy cả thế giới |

### Bắt buộc KHÔNG tách (dù file dài)

| Giữ nguyên | Vì sao tách là tệ |
|------------|-------------------|
| Chuỗi bước tính lương tuần tự trong một service rõ ràng | Tách lung tung → sai thứ tự, khó đối chiếu Excel |
| Một component màn hình AG-Grid + toolbar cùng state | Tách 5 file → sửa 1 cột phải nhảy 5 chỗ |
| `policy_packages.payload` schema + validator gắn nhau | Tách xa → lệch contract JSON |
| Mapping cột Excel ↔ field nội bộ (một bảng map) | Hai bảng map = bug âm thầm |
| File đã ổn định, ít đổi, chỉ dài vì nhiều hằng số seed | Tách “cho đẹp” không giảm rủi ro |

### Quy trình khi AI muốn tách file

```
1. Nêu lý do nghiệp vụ / cô lập lỗi (không nói "file hơn N dòng")
2. Nêu ranh giới: input/output sau tách
3. Nếu không giải thích được lợi ích → KHÔNG tách
4. Báo cáo phiên: ghi rõ đã tách gì và vì sao
```

### Cây thư mục (mục 6.5) mang ý nghĩa gì?
- Là **ranh giới module**, không phải lệnh “mỗi hàm một file”.
- Bên trong mỗi module, AI được giữ file lớn nếu đó là **một đơn vị gắn kết** (cohesion cao).

## 6.7 Bảo mật tối thiểu

- HTTPS (cloud)
- JWT expiry + refresh
- Worker và Staff tách audience token
- Rate limit login
- Audit log: ai sửa lương, ai đổi policy, ai mở khóa phiếu
- Backup DB

*Tiếp: `07_SCHEMA_DATABASE.md`*
