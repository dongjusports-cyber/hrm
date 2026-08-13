# Update UI/UX — Báo cáo tư vấn DJ HRM

> **Ngày:** 2026-08-13  
> **Đối tượng:** Ban lãnh đạo · HR · Kế toán lương · Đối tác triển khai  
> **Mục đích:** So sánh công nghệ giao diện **hiện tại** vs **hướng nâng cấp**, cách làm an toàn  
> **Tham chiếu:** `V1_0_DINH_NGHIA.md` · `23_UI_MAN_HINH.md` · `06_CONG_NGHE_KIENTRUC.md` · `BAO_CAO_UI_UX_20260812_PM.md`

---

## 1. Tóm tắt 1 trang (đem đi họp)

| | **Hiện tại (v1.0)** | **Sau v1.0 (đề xuất)** |
|---|---|---|
| **Mục tiêu** | Go-live thay GenusSuite — đủ nghiệp vụ, ổn định | Giao diện hiện đại, thao tác nhanh, dễ bảo trì |
| **Frontend** | React 19 + Vite + TypeScript | Giữ React + Vite + TS |
| **Style** | CSS thuần (`global.css`) | **Tailwind CSS** + **shadcn/ui** (Radix) |
| **Bảng lớn** | **AG-Grid v33** | **Giữ AG-Grid** — không đổi |
| **Form / overlay** | Component tự viết + CSS | shadcn Dialog, Select, Tabs, Tooltip… |
| **Backend** | FastAPI + PostgreSQL | **Không đổi** |
| **Thời điểm** | **Đang chạy** | **Sau khi đóng v1.0** (phiên riêng) |

**Quyết định đã chốt:** Không nâng UI Modern **trước** khi v1.0 xong (lương neo 1519, nghiệm thu 0 FAIL, HR pilot 1 tháng).

---

## 2. Công nghệ hiện tại — đang dùng

### 2.1 Stack web (`apps/web`)

| Thành phần | Phiên bản / công nghệ | Vai trò |
|------------|----------------------|---------|
| Framework | React 19 | SPA Portal HR + Worker |
| Build | Vite 6 | Dev nhanh, bundle production |
| Ngôn ngữ | TypeScript 5.8 | Type-safe |
| Routing | React Router 7 | Portal Lv1 → Lv4 |
| Lưới dữ liệu | AG-Grid Community 33 | Danh sách NV (~450 dòng), bảng lương (~40 cột), chấm công |
| Style | **CSS thuần** — một file `global.css` lớn | Layout fixed-viewport, toolbar, overlay hồ sơ |
| Test UI | Vitest | Unit test component nhỏ |
| Font / màu | Be Vietnam Pro · Navy `#1e40af` · nền `#f8fafc` | Theo `02_UI_PORTAL` §2.8 |

### 2.2 Điểm mạnh

- **AG-Grid** xử l tốt bảng lương 347 NV × 40 cột — cuộn ảo, lọc, resize cột.
- **FullScreenSheet** hồ sơ NV: tab mượt, Lưu không nhảy trang (đã audit 12/08).
- **Không phụ thuộc** thư viện UI nặng → build nhẹ, Docker web ~5173 ổn định.
- Backend tách biệt — đổi skin frontend **không đụng** engine lương.

### 2.3 Hạn chế (đã ghi audit 12/08)

| Hạng mục | Trạng thái |
|----------|------------|
| Toolbar HR/Lương/Chấm công trên laptop **1366×768** | Đã cải thiện (U4 Done) — cần duy trì khi thêm nút |
| Dropdown / form tự viết | Thiếu chuẩn accessibility (focus, ARIA) so với Radix |
| Design token rải rác trong CSS | Khó đổi theme đồng bộ toàn app |
| Mỗi màn tự style nút, field | Tốn công đồng bộ khi thêm màn mới |

*Các mục P0 audit (FAB AI, dropdown phụ cấp, double-click mở hồ sơ) — **đã sửa code**.*

---

## 3. Hướng nâng cấp — công nghệ đề xuất

### 3.1 Stack «UI Modern» (khuyến nghị)

| Thành phần | Công nghệ | Lý do chọn |
|------------|-----------|------------|
| Utility CSS | **Tailwind CSS v4** | Class theo design token; responsive 1366/1920; ít file CSS thủ công |
| Component kit | **shadcn/ui** | Copy vào repo (không lock vendor); Radix accessibility; Button, Dialog, Select, Sheet… |
| Primitive a11y | **Radix UI** | Focus trap overlay, keyboard, screen reader |
| Bảng lớn | **AG-Grid** (giữ) | Hiến pháp §23.10: **không đổi** sang table khác |
| Icon | **Lucide React** | Cùng hệ shadcn, nhẹ |
| Form (tuỳ chọn) | **React Hook Form + Zod** | Validate hồ sơ NV, tăng lương — type-safe với API |

### 3.2 Không đề xuất đổi

| Giữ nguyên | Vì sao |
|------------|--------|
| FastAPI / PostgreSQL / Redis | Engine nghiệp vụ ổn định, 347+ pytest |
| AG-Grid | Duy nhất đáp ứng bảng lương quy mô công ty |
| React Router cấu trúc Portal | Đúng Hiến pháp 02§ phân cấp Lv1–Lv4 |
| PWA Worker (`/worker`) | Tách audience; nâng cấp **sau** staff portal |

### 3.3 So sánh trực quan (khái niệm)

```
HIỆN TẠI                          SAU NÂNG CẤP
────────────────────────          ────────────────────────────
global.css (~1000+ dòng)    →     tailwind.config + CSS variables
.btn-primary tự định nghĩa  →     <Button variant="default">
<select> HTML + CSS         →     <Select> Radix + style đồng bộ
FullScreenSheet custom      →     <Sheet> shadcn (hoặc giữ shell, skin shadcn)
AG-Grid + theme alpine      →     AG-Grid + theme khớp token Tailwind
```

*Có thể làm mockup 2 màn (Danh sách NV + Hồ sơ) trước khi code hàng loạt.*

---

## 4. Phạm vi UX — ưu tiên màn hình

Theo tần suất HR dùng hàng ngày (`23_UI_MAN_HINH.md`):

| Ưu tiên | Màn | Việc UX |
|---------|-----|---------|
| **P1** | Danh sách nhân viên | Toolbar gọn; cột tiền; mở hồ sơ nhanh |
| **P1** | Hồ sơ NV (overlay) | 5 cột không cuộn trang; phụ cấp add/xóa; undo |
| **P1** | Bảng lương kỳ | AG-Grid theme; cột Δ màu; export |
| **P2** | Chấm công — bảng ngày | Tab gom; full-width; ít split panel |
| **P2** | Portal 8 ô | Card đồng bộ; shortcut Ctrl+K |
| **P3** | Admin · Audit · Simulate | Form shadcn; bảng phụ AG-Grid hoặc Table nhỏ |

**Nguyên tắc thiết kế (đã thống nhất):**

- Viewport chuẩn: **1920×1080** (máy HR) và **1366×768** (laptop).
- Lưới **cuộn trong vùng dữ liệu**, không cuộn cả trang.
- Tone: sáng, chuyên nghiệp — **không** hiệu ứng prototype «vũ trụ».

---

## 5. Cách làm — lộ trình triển khai

### Giai đoạn 0 — Điều kiện tiên quyết (bắt buộc)

- [ ] **v1.0 đóng:** `nghiem_thu_hien_phap` 0 FAIL · MSNV 1519 kỳ 07/2026 = **9.682.398**
- [ ] HR pilot **≥ 1 kỳ lương** trên stack hiện tại
- [ ] Backup DB trước mọi thay đổi lớn

### Giai đoạn 1 — Nền tảng (1–2 tuần dev)

1. Cài Tailwind + postcss vào `apps/web`
2. Khởi tạo shadcn/ui (`components/ui/`)
3. Map token Hiến pháp → `tailwind.config`: primary, surface, danger…
4. **Không** xóa `global.css` ngay — chạy song song (coexistence)

### Giai đoạn 2 — Pilot 1 màn (1 tuần)

- Chọn **một** màn ít rủi ro: ví dụ Portal hub hoặc màn Admin nhỏ
- Vitest + test tay 1366/1920
- HR feedback → chỉnh token trước khi lan rộng

### Giai đoạn 3 — Lõi nghiệp vụ (3–5 tuần)

| Tuần | Màn | Ghi chú |
|------|-----|---------|
| 1 | Toolbar + shared Button/Input | Dùng chung HR/Lương/TK |
| 2 | Hồ sơ NV — form + Sheet | Giữ logic API; đổi shell + control |
| 3 | AG-Grid theme wrapper | Class header/cell khớp Tailwind |
| 4–5 | Lương + Chấm công | Regression pytest API; vitest web |

### Giai đoạn 4 — Dọn dẹp

- Gỡ CSS legacy không còn reference
- Cập nhật `23_UI_MAN_HINH.md` §23.10
- Tài liệu onboarding dev mới

### Nguyên tắc an toàn

```
┌─────────────────────────────────────────────────────────┐
│  CHỈ ĐỔI apps/web — KHÔNG ĐỔI apps/api engine lương     │
│  Một PR = một module UI (hr | payroll | timekeeping)    │
│  Mỗi PR: vitest + pytest smoke + HR sign-off 1 luồng     │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Ước lượng & rủi ro

### Effort (1 dev full-time, đã quen repo)

| Hạng mục | Ước lượng |
|----------|-----------|
| Nền Tailwind + shadcn | 3–5 ngày |
| Skin toàn Portal + 3 module chính | 4–6 tuần |
| Worker PWA (mobile CN) | +1–2 tuần (phase riêng) |

### Rủi ro & giảm thiểu

| Rủi ro | Giảm thiểu |
|--------|-------------|
| Regression layout 1366 | Checklist viewport cố định mỗi PR |
| AG-Grid lệch theme | Wrapper CSS variables; không fork grid |
| Trộn Tailwind + CSS cũ | Module-by-module; không refactor một lần |
| HR mất quen | Pilot 1 màn; giữ phím tắt Esc, Ctrl+K, F2 |
| Trì hoãn go-live | **Chỉ bắt đầu sau v1.0** |

---

## 7. Lựa chọn thay thế (nếu không dùng shadcn)

| Phương án | Ưu | Nhược |
|-----------|-----|-------|
| **A. Tailwind + shadcn** (khuyến nghị) | Chuẩn cộng đồng, a11y, copy vào repo | Học curve Tailwind |
| **B. Chỉ mở rộng CSS hiện tại** | Không thêm dependency | Vẫn rải rác; khó scale 30+ màn |
| **C. Ant Design / MUI** | Component đầy đủ | Nặng; khó khớp AG-Grid; lock vendor |

Hiến pháp `20§20.8` giao **lập trình viên tự chọn** Tailwind hay CSS thuần — báo cáo này khuyến nghị **A** sau v1.0.

---

## 8. Checklist tư vấn — câu hỏi cho ban quản lý

1. **Có chấp nhận hoãn UI Modern đến sau go-live v1.0 không?** (đã chốt: Có)
2. **Laptop HR chuẩn 1366 hay 1920?** → ảnh hưởng breakpoint
3. **Pilot HR:** ai ký duyệt màn hình mới trước khi rollout?
4. **Mobile công nhân:** cùng đợt hay phase 2 (`/worker`)?
5. **Ngân sách:** 1 dev nội bộ vs thuê UI 4–6 tuần?

---

## 9. Tài liệu liên quan trong repo

| File | Nội dung |
|------|----------|
| `V1_0_DINH_NGHIA.md` | Phạm vi v1.0 vs UI sau |
| `23_UI_MAN_HINH.md` | Chuẩn pixel, toolbar, hồ sơ 5 cột |
| `BAO_CAO_UI_UX_20260812_PM.md` | Audit chi tiết P0–P3 |
| `canvases/emp-profile-layout.canvas.tsx` | Wireframe bố cục hồ sơ đề xuất |
| `06_CONG_NGHE_KIENTRUC.md` | Stack bắt buộc backend |

---

## 10. Kết luận đề xuất

1. **Giữ stack v1.0** đến khi nghiệm thu lương + HR pilot xong.  
2. **Sau v1.0:** nâng **Tailwind + shadcn/ui**, **giữ AG-Grid + FastAPI**.  
3. Triển khai **theo module**, pilot 1 màn, không big-bang.  
4. Mục tiêu UX: HR thao tác **nhanh trên 1366**, không cuộn trang, form/hồ sơ **một màn nhìn đủ**.

---

## Phụ lục A — Toàn bộ công nghệ DJ-HRM v1.0 (chi tiết)

> Nguồn: `06_CONG_NGHE_KIENTRUC.md` · `requirements.txt` · `package.json` · `docker-compose.yml` · CI  
> Cập nhật: **2026-08-13**

### A.1 Kiến trúc tổng thể

| Lớp | Công nghệ | Ghi chú |
|-----|-----------|---------|
| Kiến trúc | **Modular Monolith** | FastAPI modules: mdm, payroll, attendance, policy, ai… |
| Triển khai local | **Docker Compose** | 4 service: postgres, redis, api, web |
| Triển khai cloud (kế hoạch) | VPS + **Nginx** + SSL | Reverse proxy HTTPS |
| Agent on-prem | Python trên **Windows 10** | Đọc SQL Server Mitapro, đẩy lên API |

### A.2 Backend API (`apps/api`)

| Thành phần | Phiên bản | Vai trò |
|------------|-----------|---------|
| Ngôn ngữ | **Python 3.12** | Runtime |
| Web framework | **FastAPI 0.115** | REST API, OpenAPI |
| ASGI server | **Uvicorn 0.34** | Dev `--reload`, production |
| ORM | **SQLAlchemy 2.0** | Models, query |
| Migration DB | **Alembic 1.15** | Schema versioned |
| Driver PostgreSQL | **psycopg 3.2** | Kết nối DB |
| Validation / config | **Pydantic 2.11** + pydantic-settings | Schema API, `.env` |
| Auth | **JWT** (python-jose) + **bcrypt** (passlib) | Login, RBAC |
| Cache / queue | **Redis 7** (client redis 5.2) | Session, job (sẵn sàng) |
| HTTP client | **httpx 0.28** | Gọi Gemini, agent |
| Upload form | python-multipart | Import Excel |
| Template in | **Jinja2 3.1** | Hợp đồng, quyết định HTML |
| Excel | **openpyxl 3.1** + xlrd 2.0 | Import/export bảng lương, NV |
| Tiền tệ | **`decimal.Decimal`** | Bắt buộc — không float lương |
| Test | **pytest 8.3** | 347+ test (CI + local) |

### A.3 Cơ sở dữ liệu & tích hợp

| Thành phần | Công nghệ | Vai trò |
|------------|-----------|---------|
| DB chính | **PostgreSQL 16** (Alpine) | NV, lương, chấm công, policy JSONB |
| DB nguồn (read-only) | **Microsoft SQL Server** (Mitapro) | Giờ chấm vân tay Ronald Jack |
| Agent driver | **pyodbc 5.2** + ODBC Driver 17/18 | Agent Windows đọc Mitapro |
| Legacy thay thế | GenusSuite (Oracle/ASP cũ) | Chỉ tham chiếu migration dữ liệu |

### A.4 Frontend web (`apps/web`)

| Thành phần | Phiên bản | Vai trò |
|------------|-----------|---------|
| UI library | **React 19** | SPA |
| Build | **Vite 6** | Dev HMR, production bundle |
| Ngôn ngữ | **TypeScript 5.8** | Type-safe |
| Routing | **React Router 7** | Portal Lv1–Lv4, Worker PWA |
| Lưới lớn | **AG-Grid Community 33** | HR list, lương, chấm công |
| Style | **CSS thuần** (`global.css`) | Chưa Tailwind (v1.0) |
| QR (Worker) | **qrcode 1.5** | Phiếu lương / xác nhận |
| Test | **Vitest 3.0** | 25+ unit test UI |
| Font | **Be Vietnam Pro** (Google Fonts) | UI tiếng Việt |

### A.5 Agent đồng bộ (`apps/agent`)

| Thành phần | Phiên bản | Vai trò |
|------------|-----------|---------|
| Runtime | Python 3.12 (Windows) | Chạy cùng máy Mitapro |
| HTTP | httpx | POST punch lên API cloud/local |
| Config | pydantic-settings + dotenv | Lịch sync, token |
| SQL | pyodbc | `CheckInOut`, `NHANVIEN`… |
| Test | pytest | Agent unit test |

### A.6 AI & tự động hóa

| Thành phần | Công nghệ | Vai trò |
|------------|-----------|---------|
| LLM | **Google Gemini** (`gemini-2.0-flash`) | Trợ Lý AI HR — read-only, giới hạn/ngày |
| API | Google Generative Language REST | Qua `GEMINI_API_KEY` |
| CI | **GitHub Actions** | Push/PR → tsc + vite build + vitest + pytest |

### A.7 DevOps & môi trường

| Thành phần | Chi tiết |
|------------|----------|
| Container | Docker Desktop (Win10) · Linux VPS (cloud) |
| Web dev port | **5173** (Vite) |
| API port | **8000** (Uvicorn) |
| DB port | **5432** (Postgres) |
| Redis port | **6379** |
| Version control | **Git** · nhánh `main` |
| CI Node | 22 · CI Python | 3.12 |

### A.8 Module nghiệp vụ (logic, không phải lib riêng)

| Module API | Chức năng chính |
|------------|-----------------|
| `mdm` | Nhân viên, tổ chức, lookup, import Excel |
| `attendance` | Bảng công, punch, Mitapro sync |
| `payroll` | Engine lương, payslip, export Genus format |
| `policy` | Gói chính sách JSON metadata-driven |
| `insurance` | BHXH, khai báo |
| `worker` | Portal công nhân, phiếu lương, khiếu nại |
| `ai` | Gemini query, FAB Trợ Lý |
| `audit` | Nhật ký thao tác |
| `print` | In HĐ, quyết định, phụ lục tăng lương |
| `integration` | Agent ingest, punch resolver |

### A.9 Công nghệ **chưa** dùng (v1.0) — chỉ đề xuất sau go-live

| Công nghệ | Trạng thái |
|-----------|------------|
| Tailwind CSS | Chưa cài |
| shadcn/ui · Radix | Chưa cài |
| TanStack Query / Table | Chưa cài |
| Ant Design · MUI | Không chọn |
| Celery / ARQ worker | Redis có; worker queue chưa bật đầy đủ |

*Tài liệu stack đầy đủ nhất trong repo: **`06_CONG_NGHE_KIENTRUC.md`**.*

---

*Báo cáo tư vấn — có thể in/PDF đem họp. Cập nhật khi chốt ngân sách hoặc mockup 2 màn so sánh.*
