# Bàn giao máy nhà → USB → máy công ty (2026-08-11 buổi tối)

> **Mục đích:** Copy folder `dj-hrm` sang ổ cứng di động, mai mở Cursor tại công ty làm tiếp.  
> **Đọc kèm:** `HUONG_DAN_USB_VA_MAY_CONG_TY_20260811.md`

---

## 1. Đã làm trên máy nhà (phiên tối 11/08)

| Hạng mục | Trạng thái |
|----------|------------|
| Git checkpoint trước overlay | `7b0f761` |
| Overlay hồ sơ NV (5 cột, khung cuộn, bỏ header) | **`013f69f`** |
| DB máy nhà restore từ backup công ty + chỉnh tay | ~453 NV (kiểm tra lại sau backup) |

---

## 2. Backup đã tạo (trong folder `dj-hrm`)

| File | Mô tả |
|------|--------|
| `backups/djhrm_20260811_232823.dump` | `pg_dump -Fc` — restore bằng `ops/restore.ps1` |
| `djhrm_backup_20260811_may_nha.sql` | SQL plain **UTF-8** (~4.0 MB) — 453 NV |
| `.git/` | Lịch sử commit — **copy cùng folder** |

**Không** để `.env` lên USB công khai. Ổ di động cá nhân: có thể copy `.env` để chạy nhanh.

---

## 3. Copy sang ổ cứng di động

```text
D:\dj-hrm\dj-hrm\   →   (ổ di động)\dj-hrm\
```

**Nên copy nguyên folder** (gồm `node_modules`, `.venv`, `.git`, `HIEN_PHAP`, `backups`, file `.sql` gốc).

---

## 4. Mai trên máy công ty — bước nhanh

1. Dán folder vào ổ làm việc (vd. `D:\dj-hrm\dj-hrm`).
2. Cursor → Open Folder → thư mục `dj-hrm`.
3. **New Chat** → dán khối «Tóm tắt cho AI» ở mục 6.
4. **KHÔNG** chạy `load_org_structure` / `import_genussuite_2026` trên DB công ty thật.
5. Nếu DB công ty cũ hơn code: `docker compose exec api alembic upgrade head` (nhờ AI/IT).
6. Web: `docker compose up -d --build web` hoặc theo README.

---

## 5. Nợ / việc cần làm trên **máy công ty**

### Ưu tiên cao (UI vừa làm — cần màn rộng + DB thật)

| # | Việc | Ghi chú |
|---|------|---------|
| 1 | **Nghiệm thu overlay hồ sơ NV** | MSNV 1496 / 1514: tab cố định, khung vàng cuộn, 5 cột, Lưu/In/Đóng trên hàng tab |
| 2 | **Tinh chỉnh tỷ lệ 5 cột** | Nếu cột BH hoặc địa chỉ vẫn chật — chỉnh CSS `emp-profile-cols-weighted` |
| 3 | **Phụ cấp trên DB công ty** | Chạy trên bản sao trước: `reseed_pay_component_names` + `import_allowances_salary_summary` — **không** ghi đè DB thật nếu HR chưa duyệt |
| 4 | **Đối chiếu MSNV 1519** | ATTEND / TRANSPORT / thâm niên / TOXIC vs GenusSuite |

### Trung hạn (hiến pháp / nghiệm thu)

| # | Việc | Ghi chú |
|---|------|---------|
| 5 | **22 mục nghiệm thu HR** (SKIP) | `docker compose exec api python -m app.scripts.nghiem_thu_hien_phap` |
| 6 | **Mitapro / Agent** | Chỉ test được mạng nội bộ công ty |
| 7 | **~74 tên NV mojibake** | Ngoài file Excel — script `fix_utf8_mojibake` đã có, cần rà soát thêm |
| 8 | **Mobile hồ sơ NV** | 1 cột + cuộn trong khung — chưa polish |

### Cấm / cẩn thận

- **Không** `load_org_structure` / full `import_genussuite_2026` trên DB công ty đã có 438+ NV thật.
- Restore SQL: dùng file **UTF-8** (`djhrm_backup_20260811_may_nha.sql`), **không** copy UTF-16 trực tiếp từ `pg_dump` PowerShell cũ.

---

## 6. Tóm tắt 1 khối cho AI (copy vào chat công ty)

```text
Dự án DJ HRM — folder dj-hrm (USB từ máy nhà 2026-08-11 tối).

Đã có Git: `7b0f761` + `013f69f` (overlay hồ sơ NV).
DB backup: `backups/djhrm_20260811_232823.dump` + `djhrm_backup_20260811_may_nha.sql` (UTF-8, 453 NV).

Đọc: HIEN_PHAP/BAO_CAO_BAN_GIAO_MAY_NHA_20260811_PM.md và HUONG_DAN_USB_VA_MAY_CONG_TY_20260811.md.

DB công ty = dữ liệu thật — KHÔNG chạy load_org_structure / import_genussuite_2026.

Việc tiếp:
1) Nghiệm thu UI hồ sơ NV (1496/1514) trên màn công ty
2) Phụ cấp / MSNV 1519 trên DB thật (có backup trước)
3) 22 mục nghiệm thu HR còn SKIP
4) Mitapro nội bộ

Bắt đầu bằng mở hồ sơ NV, xác nhận khung vàng cuộn đúng, rồi báo chỗ cần chỉnh cột.
```

---

*Sinh tự động khi backup máy nhà — cập nhật commit hash sau khi `git commit`.*
