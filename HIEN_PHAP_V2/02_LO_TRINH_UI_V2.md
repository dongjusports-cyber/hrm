# 02 — Lộ trình UI V2 (chi tiết)

> Song song UAT 1 tháng — **chỉ tài liệu + nhánh `feat/ui-v2`** cho đến khi scaffold được duyệt code.

---

## Tổng quan 8 tuần (ước lượng)

| Tuần | Việc | Deliverable |
|------|------|-------------|
| **0** | Hiến pháp V2 + archive V1 | `HIEN_PHAP_V2/` *(đang làm)* |
| **1** | Scaffold `apps/web-v2` + Docker 5174 | Chạy «Hello Portal» |
| **2** | Tailwind token + shadcn base | Button, Input, Sheet, Select |
| **3** | **Portal 8 ô** V2 | So sánh visual với 5173 |
| **4** | **Danh sách NV** + AG-Grid theme | Lọc, cột, mở hồ sơ |
| **5** | **Hồ sơ NV** overlay | 5 cột, phụ cấp, Lưu |
| **6** | **Chấm công + Lương** (lưới chính) | Không đổi logic API |
| **7** | Worker `/worker`, polish 1366 | Vitest pass |
| **8** | Merge sau UAT | `05` checklist |

*Tuần 1–7 trùng lịch UAT — không ảnh hưởng 5173.*

---

## Tuần 1 — Scaffold (bước code đầu tiên)

1. `git checkout -b feat/ui-v2`
2. Copy cấu trúc tối thiểu từ `apps/web`:
   - `package.json`, `vite.config.ts`, `tsconfig`, `index.html`
   - Port **5174**, proxy `/api` → `api:8000`
3. Cài Tailwind v4 + shadcn init
4. `docker-compose.yml` thêm service `web-v2`
5. Trang login + Portal shell (chưa nghiệp vụ)

**Nghiệm thu tuần 1:** Mở `:5174/login` → đăng nhập `hr.demo` → thấy 8 ô (placeholder).

---

## Tuần 2–3 — Design system

- Map token từ `HIEN_PHAP/02_UI_PORTAL` §2.8:
  - Primary `#1e40af`, nền `#f8fafc`, font Be Vietnam Pro
- Component: `Button`, `Input`, `Label`, `Select`, `Dialog`, `Sheet`, `Tabs`, `Tooltip`
- Layout: fixed viewport `.hr-shell` tương đương §23

---

## Tuần 4–6 — Module nghiệp vụ (copy logic, đổi skin)

| Module | Nguồn logic | Ghi chú |
|--------|-------------|---------|
| HR | `apps/web/src/modules/hr/` | AG-Grid giữ nguyên |
| Timekeeping | `modules/timekeeping/` | Tab Đồng bộ giữ flow |
| Payroll | `modules/payroll/` | Cột tiền canh phải |

**Không viết lại API client** — copy `shared/api.ts` hoặc symlink / package `@dj-hrm/api-client` (tuỳ chọn tuần 2).

---

## Tuần 7 — Responsive & test

- Viewport **1366×768** và **1920×1080** (§23)
- Vitest component cơ bản
- HR **không** test — chỉ Chủ xem 5174

---

## Tuần 8 — Chờ UAT xong

Thực hiện `05_CHECKLIST_MERGE_SAU_V1.md`.

---

## Milestone «dừng V2»

Dừng mở rộng V2 nếu:

- UAT phát hiện bug P0 backend — ưu tiên `main` + `api`
- HR chưa ký nhưng đã merge nhầm → rollback

---

*Tiếp: `03_STACK_UI_V2.md`*
