# 01 — Nguyên tắc song song (UAT + UI V2)

> **Một quy tắc:** HR chỉ thấy **một** phần mềm — port **5173**. Mọi thứ khác là «phòng lab».

---

## 1. Bản HR đang chạy (đóng băng UI)

| Hạng mục | Giá trị cố định |
|----------|-----------------|
| Folder | `apps/web` |
| Git | nhánh **`main`** |
| URL | `http://192.168.1.123:5173` (hoặc IP máy Docker) |
| Docker service | `web` |
| Tài khoản test | `hr.demo` / `hr1` / `hr2` (HR thật) |

**Trong 1 tháng UAT — CẤM trên bản này:**

- Cài Tailwind / shadcn vào `apps/web`
- Refactor lớn `global.css`, layout hồ sơ NV
- `docker compose up --build web` giữa giờ HR đang làm (trừ hotfix bug đã báo trước)
- Merge nhánh `feat/ui-v2` vào `main`

**ĐƯỢC:**

- Sửa **bug** lương/công/API (P0/P1) có MSNV + kỳ + số mong đợi
- Seed/migrate **dữ liệu** đã HR duyệt (PCCC/HSE…)
- Backup DB trước khi sửa

---

## 2. Bản UI V2 (phòng lab)

| Hạng mục | Giá trị |
|----------|---------|
| Folder | `apps/web-v2` *(tạo khi bắt đầu code)* |
| Git | nhánh **`feat/ui-v2`** |
| URL | `http://192.168.1.123:5174` |
| Docker service | `web-v2` *(thêm sau)* |
| Ai dùng | Chủ + Cursor — **không đưa link cho HR** |

**Chỉ đổi giao diện** — gọi **cùng API** `/api/...` như bản 5173.

---

## 3. Backend & DB (chung)

| Hạng mục | Quy tắc |
|----------|---------|
| `apps/api` | Dùng chung; ưu tiên **ổn định** cho UAT |
| Migration Alembic | Chỉ khi **bắt buộc** (bug/luật đã chốt); backup trước |
| Không | Đổi contract API để «UI đẹp hơn» |

---

## 4. Git workflow

```text
main           ← HR UAT, bugfix only
  │
  └── feat/ui-v2   ← toàn bộ UI V2
         │
         └── cherry-pick bugfix từ main (nếu cần)
```

- PR UI V2 → `main`: **sau** HR ký UAT (`05_CHECKLIST_MERGE_SAU_V1.md`)
- Bugfix UAT: commit trực tiếp `main` (hoặc `fix/*` merge nhanh)

---

## 5. Docker (khi có web-v2)

```text
5173  web      → HR
5174  web-v2   → Dev UI
8000  api      → Chung
```

HR **không** cần biết port 5174 tồn tại.

---



---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
*Tiếp: `02_LO_TRINH_UI_V2.md`*
