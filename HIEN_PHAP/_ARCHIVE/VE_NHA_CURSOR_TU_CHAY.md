# Về nhà — Cursor tự chạy (chỉ cần 1 câu chat)

> Ngày backup: **2026-08-11** · File DB: `djhrm_backup_20260811.sql` (~4,8 MB)

---

## Bạn chỉ cần làm 3 việc (không cần hiểu lệnh)

1. **Dán** cả folder `dj-hrm` từ USB vào máy nhà (vd. `D:\dj-hrm\dj-hrm`).
2. Mở **Cursor** → **File → Open Folder** → chọn folder `dj-hrm`.
3. **Chat mới** → gõ **đúng 1 dòng** này:

```text
Đọc file HIEN_PHAP/VE_NHA_CURSOR_TU_CHAY.md và thực hiện hết các bước trong mục "CHO AI" giúp tôi. Chạy lệnh thật trên máy, báo kết quả từng bước.
```

Xong. Cursor sẽ tự chạy Docker, restore DB, kiểm tra.

---

## CHO AI — thực thi tuần tự (đọc kỹ trước khi chạy)

Bạn là agent trên máy nhà user. Folder dự án = workspace root (`dj-hrm`).  
User **không rành kỹ thuật** — giải thích ngắn gọn bằng tiếng Việt sau mỗi bước.

### Trạng thái khi backup từ máy công ty

- 453 nhân viên (354 active, 99 resigned), 10 bộ phận, 30 tổ active
- 453 hợp đồng lao động (`labour_contracts`)
- Migration Alembic tới **0046**; pytest ~300 passed
- Nghiệm thu auto: `nghiem_thu_hien_phap` — 10 OK; MSNV **1519** lương **9.682.398** khớp DB
- Backup SQL: **`djhrm_backup_20260811.sql`** nằm **ngay trong root** folder `dj-hrm`

### CẤM chạy các script sau (sẽ phá DB đã restore)

- `load_org_structure` / import cây tổ chức full
- `import_genussuite_2026` hoặc nạp GenusSuite full
- `seed_current_labour_contracts` — **chỉ chạy nếu** sau restore bảng `labour_contracts` **trống** (0 dòng)

---

### Bước 0 — Kiểm tra file

Chạy và báo user:

```powershell
cd $PWD
Test-Path .\djhrm_backup_20260811.sql
Test-Path .\.env
Test-Path .\docker-compose.yml
```

- Thiếu `.sql` → dừng, bảo user copy lại từ USB.
- Thiếu `.env` → copy `.env.example` thành `.env`, nhắc user điền mật khẩu (hoặc dùng mặc định local nếu `.env.example` đủ).

---

### Bước 1 — Docker

```powershell
docker compose up -d --build
```

Đợi postgres healthy (tối đa ~60 giây). Kiểm tra:

```powershell
docker compose ps
```

---

### Bước 2 — Restore database

**Chỉ restore khi DB mới/trống** hoặc user xác nhận ghi đè local.

Kiểm tra số NV hiện tại:

```powershell
docker compose exec -T postgres psql -U djhrm djhrm -c "SELECT COUNT(*) FROM employees;"
```

- Nếu **0** hoặc user muốn ghi đè → restore:

```powershell
Get-Content .\djhrm_backup_20260811.sql | docker compose exec -T postgres psql -U djhrm djhrm
```

- Nếu đã có **~453** NV → **bỏ qua restore**, báo "DB đã có dữ liệu".

Sau restore, xác nhận:

```powershell
docker compose exec -T postgres psql -U djhrm djhrm -c "SELECT COUNT(*) AS employees FROM employees; SELECT COUNT(*) AS contracts FROM labour_contracts;"
```

Kỳ vọng: **employees ≈ 453**, **contracts ≈ 453**.

---

### Bước 3 — Migration (an toàn, không mất data)

```powershell
docker compose exec api alembic upgrade head
```

---

### Bước 4 — Kiểm tra nghiệm thu tự động

```powershell
docker compose exec api python -m app.scripts.nghiem_thu_hien_phap
```

Báo user: bao nhiêu **OK** / **SKIP** / **FAIL**. FAIL → sửa và giải thích ngắn.

---

### Bước 5 — Mở thử (báo user)

- Web: http://localhost:5173
- API docs: http://localhost:8000/docs
- Đăng nhập Admin (xem `.env`: `ADMIN_USERNAME` / `ADMIN_PASSWORD`)

---

### Bước 6 — Việc tiếp theo (hỏi user sau khi xong bước 1–5)

- 22 mục nghiệm thu **HR** (Mitapro, Excel, Admin…) — cần mạng công ty / HR bấm thử
- Đọc thêm `HIEN_PHAP/` và `BAO_CAO_BAN_GIAO_MAY_NHA_20260810.md` để làm tiếp hiến pháp
- **Mitapro / vân tay Ronald Jack** không chạy được ở nhà nếu không có mạng nội bộ công ty

---

### Lỗi thường gặp — AI tự xử lý

| Triệu chứng | Cách xử lý |
|-------------|------------|
| `docker` không nhận lệnh | Bảo cài Docker Desktop, bật WSL2, khởi động lại |
| Container `postgres` không healthy | `docker compose logs postgres` — thường do port 5432 bị chiếm |
| Restore báo lỗi "already exists" | DB chưa trống — drop/recreate **chỉ khi** user đồng ý mất data local |
| `.venv` / `node_modules` lỗi | `docker compose` vẫn chạy được; hoặc `pip install -r apps/api/requirements.txt` và `npm install` trong `apps/web` |
| Thiếu `labour_contracts` sau restore | Chạy **một lần**: `docker compose exec api python -m app.scripts.seed_current_labour_contracts` |

---

## Tóm tắt 1 dòng (dán chat nếu quên)

```text
Đọc HIEN_PHAP/VE_NHA_CURSOR_TU_CHAY.md — mục CHO AI — và chạy hết giúp tôi.
```

---

*File này đi cùng USB. Không cần GitHub.*
