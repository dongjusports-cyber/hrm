# Máy công ty — Cursor tự chạy (chỉ cần 1 câu chat)

> Ngày USB từ máy nhà: **2026-08-11 tối** · Git: `7b0f761` + `013f69f`  
> Code overlay hồ sơ NV · DB công ty **giữ nguyên** (dữ liệu thật)

---

## Bạn chỉ cần làm 3 việc (không cần hiểu lệnh)

1. **Dán** cả folder `dj-hrm` từ USB vào máy công ty (vd. `D:\dj-hrm\dj-hrm` — **ghi đè** folder cũ nếu Cursor hỏi).
2. Mở **Cursor** → **File → Open Folder** → chọn folder `dj-hrm`.
3. **Chat mới** → gõ **đúng 1 dòng** này:

```text
Đọc file HIEN_PHAP/CONG_TY_CURSOR_TU_CHAY.md và thực hiện hết các bước trong mục "CHO AI" giúp tôi. Chạy lệnh thật trên máy, báo kết quả từng bước.
```

Xong. Cursor sẽ tự bật Docker, cập nhật code, migration, build web, kiểm tra.

---

## CHO AI — thực thi tuần tự (đọc kỹ trước khi chạy)

Bạn là agent trên **máy công ty** user. Folder dự án = workspace root (`dj-hrm`).  
User **không rành kỹ thuật** — giải thích ngắn gọn bằng tiếng Việt sau mỗi bước.

### Trạng thái code từ USB (máy nhà 11/08 tối)

- Git: `013f69f` — overlay hồ sơ NV full màn, 5 cột, khung cuộn, bỏ header đỏ
- Git: `7b0f761` — payroll full màn, script phụ cấp, checkpoint trước đó
- File handoff: `HIEN_PHAP/BAO_CAO_BAN_GIAO_MAY_NHA_20260811_PM.md`
- Backup máy nhà (chỉ dùng nếu cần khôi phục): `djhrm_backup_20260811_may_nha.sql`, `backups/djhrm_20260811_232823.dump`

### CẤM — DB công ty có dữ liệu thật

**Không** chạy các lệnh sau trừ khi user **viết rõ** «cho phép ghi đè DB»:

- `load_org_structure` / import cây tổ chức full
- `import_genussuite_2026` hoặc nạp GenusSuite full
- Restore SQL/dump từ USB **ghi đè** DB đang có hàng trăm NV
- `seed_current_labour_contracts` nếu bảng `labour_contracts` đã có dữ liệu

---

### Bước 0 — Kiểm tra file & Git

```powershell
cd $PWD
Test-Path .\docker-compose.yml
Test-Path .\.env
git log -1 --oneline
```

- Thiếu `.env` → copy `.env.example` thành `.env`, nhắc user giữ mật khẩu công ty (hoặc merge từ `.env` cũ nếu còn backup).
- Git nên thấy commit gần nhất **`013f69f`** (hoặc mới hơn).

Báo user số NV hiện tại (chưa sửa gì):

```powershell
docker compose exec -T postgres psql -U djhrm djhrm -c "SELECT COUNT(*) AS employees FROM employees;"
```

Ghi nhận số này — **không restore** nếu đã có NV (vd. 438–453).

---

### Bước 1 — Docker (bật / build)

```powershell
docker compose up -d --build
```

Đợi postgres healthy (~60 giây):

```powershell
docker compose ps
```

Nếu container `web` báo thiếu package (vd. `qrcode`):

```powershell
docker compose exec web npm install
docker compose restart web
```

---

### Bước 2 — Migration (chỉ upgrade, không drop DB)

```powershell
docker compose exec api alembic upgrade head
```

Báo revision cuối (kỳ vọng **0046** trở lên).

---

### Bước 3 — Build lại giao diện (code overlay mới)

```powershell
docker compose up -d --build web
```

---

### Bước 4 — Kiểm tra nghiệm thu tự động

```powershell
docker compose exec api python -m app.scripts.nghiem_thu_hien_phap
```

Báo user: **OK** / **SKIP** / **FAIL**. FAIL → sửa nếu được, giải thích ngắn.

---

### Bước 5 — Mở thử web (báo user)

- Web: http://localhost:5173 (hoặc IP máy công ty:5173)
- Đăng nhập Admin (`.env`: `ADMIN_USERNAME` / `ADMIN_PASSWORD`)
- Vào **Nhân Sự → Danh sách** → bấm **Họ tên** NV **1496** hoặc **1514**
- Xác nhận UI overlay:
  - Không còn header đỏ (MSNV·tên + In HĐ ở trên cùng overlay)
  - Hàng MSNV / Họ tên / Ảnh + hàng tab + Lưu / Đóng **cố định**
  - **Khung viền** phía dưới **cuộn chuột** (5 cột + phụ cấp)

---

### Bước 6 — Việc tiếp theo (sau khi bước 1–5 OK)

Đọc `HIEN_PHAP/BAO_CAO_BAN_GIAO_MAY_NHA_20260811_PM.md` mục **Nợ**. Ưu tiên:

| # | Việc |
|---|------|
| 1 | Tinh chỉnh CSS 5 cột nếu user báo chật (`emp-profile-cols-weighted`) |
| 2 | Phụ cấp MSNV 1519 — **backup trước** (`.\ops\backup.ps1`) rồi mới import |
| 3 | 22 mục nghiệm thu HR (SKIP) — HR bấm thử |
| 4 | Mitapro / Agent — mạng nội bộ |

Hỏi user muốn làm mục nào trước; **đừng** tự import phụ cấp lên DB thật nếu chưa backup + chưa được duyệt.

---

### Lỗi thường gặp — AI tự xử lý

| Triệu chứng | Cách xử lý |
|-------------|------------|
| `docker` không nhận lệnh | Bảo bật Docker Desktop, khởi động lại |
| Web overlay đỏ / crash `qrcode` | `docker compose exec web npm install` + restart web |
| Trang trắng sau copy USB | `docker compose up -d --build` |
| Chữ Việt lỗi font | `docker compose exec api python -m app.scripts.fix_utf8_mojibake` (cân nhắc, chạy 1 lần) |
| Muốn khôi phục DB từ USB | **Hỏi user xác nhận** → `.\ops\backup.ps1` backup DB hiện tại trước → restore |

---

## Tóm tắt 1 dòng (dán chat nếu quên)

```text
Đọc HIEN_PHAP/CONG_TY_CURSOR_TU_CHAY.md — mục CHO AI — và chạy hết giúp tôi.
```

---

*File này đi cùng USB từ máy nhà. Không cần GitHub.*
