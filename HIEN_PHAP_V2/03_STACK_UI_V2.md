# 03 — Stack công nghệ UI V2

> Tóm tắt tư vấn kỹ thuật — chi tiết backend xem `HIEN_PHAP/06_CONG_NGHE_KIENTRUC.md`.

---

## So sánh nhanh

| | **V1 (5173 — đang UAT)** | **V2 (5174 — lab)** |
|---|---|---|
| React + Vite + TS | Giữ | Giữ |
| Style | CSS thuần `global.css` | **Tailwind CSS v4** |
| Component | Tự viết | **shadcn/ui** (Radix) |
| Lưới lớn | AG-Grid 33 | **AG-Grid 33** (giữ) |
| Icon | Unicode / tối giản | **Lucide React** |
| Form | Controlled inputs | **React Hook Form + Zod** (tuỳ chọn) |
| Backend | FastAPI + PostgreSQL | **Không đổi** |

---

## Stack web V2 (đề xuất)

| Thành phần | Phiên bản | Vai trò |
|------------|-----------|---------|
| React | 19 | SPA |
| Vite | 6 | Build |
| TypeScript | 5.8 | Type-safe |
| React Router | 7 | Portal Lv1–Lv4 |
| Tailwind CSS | v4 | Utility + token |
| shadcn/ui | latest | Button, Sheet, Select… |
| Radix UI | (via shadcn) | Accessibility |
| AG-Grid Community | 33 | HR list, lương, công |
| Vitest | 3 | Test UI |

---

## Stack hệ thống (giữ nguyên — không đổi khi UI V2)

| Lớp | Công nghệ |
|-----|-----------|
| API | Python 3.12 · FastAPI · Uvicorn |
| ORM | SQLAlchemy 2 · Alembic |
| DB | PostgreSQL 16 · Redis 7 |
| Auth | JWT · bcrypt |
| Excel | openpyxl |
| Agent | Python · pyodbc → Mitapro (máy `.122`) |
| AI | Google Gemini 2.0 Flash |
| CI | GitHub Actions (pytest + vitest + tsc) |
| Deploy | Docker Compose |

---

## Design token (từ Hiến pháp V1 §02.8)

| Token | Giá trị |
|-------|---------|
| Font | Be Vietnam Pro |
| Primary | Navy `#1e40af` |
| Background | `#f8fafc` |
| Success / Warn / Danger | emerald / amber / red |
| Tone | Sáng, chuyên nghiệp — **không** hiệu ứng prototype |

---

## Không dùng

| Công nghệ | Lý do |
|-----------|--------|
| Ant Design / MUI full | Nặng; khó khớp AG-Grid |
| Đổi AG-Grid sang table khác | §23.10 — bảng 40 cột |
| Microservices / K8s | §11 vừa đủ ~500 NV |

---

## Tham chiếu V1

- Công thức lương: `HIEN_PHAP/03_CONG_THUC_LUONG.md`
- Pixel màn hình: `HIEN_PHAP/23_UI_MAN_HINH.md`
- Portal 8 ô: `HIEN_PHAP/02_UI_PORTAL_PHAN_QUYEN.md`

---

*Tiếp: `04_MAN_HINH_UU_TIEN.md`*
