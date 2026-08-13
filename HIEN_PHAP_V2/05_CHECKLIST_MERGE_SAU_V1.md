# 05 — Checklist merge UI V2 (sau HR ký UAT)

> Chỉ thực hiện khi **`07_UAT_HR_1_THANG.md`** đạt và Chủ xác nhận go-live UI mới.

---

## Điều kiện vào merge

- [ ] HR ký: «Kỳ lương pilot đạt» (hoặc danh sách NV lệch đã xử lý)
- [ ] MSNV **1519** neo **9.682.398** (07/2026) trên DB công ty
- [ ] `docker compose exec api python -m app.scripts.nghiem_thu_hien_phap` → **0 FAIL**
- [ ] Agent Mitapro ≥ 7 ngày ổn
- [ ] Backup DB full (`backups/djhrm_*.dump`)

---

## Bước merge (Chủ + Cursor)

### 1. Code

```text
git checkout main
git pull
git merge feat/ui-v2
# Giải quyết conflict — ưu tiên logic API từ main, UI từ feat/ui-v2
```

**Hoặc swap folder** (nếu merge quá lớn):

```text
mv apps/web apps/web-legacy
mv apps/web-v2 apps/web
# Cập nhật docker-compose: web port 5173, xóa web-v2
```

### 2. Test bắt buộc

```powershell
docker compose exec api pytest tests/ -q
cd apps/web; npm run test; npx tsc --noEmit; npm run build
```

### 3. Smoke tay (30 phút)

- Login `hr.demo`
- Mở NV → sửa → Lưu
- Chấm công kỳ hiện tại → xem tổng hợp
- Tính lương draft 1 NV mẫu

### 4. HR xác nhận lại (1 buổi)

- Cùng URL **5173** — UI mới, quy trình cũ
- Ghi nhận lỗi P0 trong 48h → hotfix `main`

### 5. Dọn dẹp

- [ ] Xóa / archive `apps/web-legacy` sau 2 tuần ổn
- [ ] Cập nhật `HIEN_PHAP/23_UI_MAN_HINH.md` §23.10 → Tailwind + shadcn
- [ ] Đóng nhánh `feat/ui-v2`

---

## Rollback (nếu lỗi nghiêm trọng)

1. `git revert` merge commit **hoặc** đổi Docker trỏ lại `web-legacy`
2. Khôi phục DB từ backup nếu migration UI đi kèm (hiếm)
3. Thông báo HR: «dùng lại giao diện cũ tạm 24h»

---

*Tiếp: `06_QUY_TAC_CHO_AI.md`*
