# 12 — Bảo mật, Backup, Vận hành (gọn, thực dụng)

## 12.1 Bảo mật dữ liệu cá nhân

| Dữ liệu nhạy cảm | Quy tắc |
|------------------|---------|
| CCCD, số tài khoản, lương, mức BHXH | Hạn chế theo quyền; không hiển thị cho user không phận sự |
| Mật khẩu | Hash bcrypt (không lưu plain) |
| API key Gemini, agent_token, DB pass | Trong biến môi trường / secrets, **không** commit git, **không** ghi log |
| Log | **Cấm** ghi lương chi tiết, mật khẩu, API key |

Mã hóa cột (CCCD/STK) = tùy chọn Phase sau nếu cần; MVP tối thiểu: phân quyền + không lộ log.

## 12.2 Đăng nhập an toàn (đủ, không phiền)

- Khóa tạm sau 5 lần sai (seed, Admin chỉnh)
- JWT hết hạn (11§11.4)
- Token worker và staff tách audience
- HTTPS bắt buộc trên cloud

## 12.3 Ai được xuất dữ liệu

| Hành động | Ai |
|-----------|-----|
| Xuất Excel bảng lương | KT lương, Admin |
| Xuất danh sách NV | HR, Admin |
| Mọi export | Ghi audit log (ai, khi nào, kỳ nào) |

## 12.4 Backup & khôi phục

| Hạng mục | Quy tắc seed |
|----------|--------------|
| Backup DB | `pg_dump` **hằng ngày**, tự động |
| Giữ | 30 ngày (Admin đổi tới 90) |
| Nơi lưu | Ổ khác / cloud storage; không cùng chỗ DB |
| RPO | Mất tối đa 24 giờ dữ liệu |
| RTO | Khôi phục trong ~4 giờ |
| Kiểm thử restore | Định kỳ (ví dụ mỗi quý) — ghi lại đã test |

Script backup/restore để trong repo (`ops/`), người không IT chạy 1 lệnh.

## 12.5 Secrets & cấu hình

- File `.env` (không commit) cho: DB, Redis, JWT secret, Gemini key, agent token.
- Có `.env.example` mẫu (giá trị giả).

## 12.6 Migration & rollback DB

- Dùng **Alembic**. Mỗi thay đổi schema = 1 revision có `upgrade` + `downgrade`.
- Trước migration production: backup trước.
- Không sửa bảng tay trên production.

## 12.7 Phát hành (đơn giản)

```
Local (test) → VPS (production)
```
- Không cần staging phức tạp giai đoạn đầu. Khi cần, thêm 1 VPS staging.
- Deploy = `docker compose pull && up -d` + chạy migration.
- Ghi tag phiên bản (v1.0, v1.1…).

## 12.8 Giám sát tối thiểu (không nặng)

- Health check `/health` (api + db + redis).
- Log lỗi ra file + xoay vòng (rotate).
- Trạng thái Agent Mitapro hiển thị trên Web.
- **Không** dựng Grafana/Prometheus giai đoạn đầu trừ khi Chủ muốn.

*Tiếp: `13_TEST_NGHIEM_THU_NGOAI_LE.md`*
