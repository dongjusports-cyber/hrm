# 15 — Runbook cho người không IT (Chủ phần mềm)

> Khi có sự cố: làm theo bước, nếu không xong → chụp màn hình + copy lỗi đưa cho AI.

## 15.1 Agent Mitapro báo ĐỎ (không đồng bộ được)

1. Kiểm tra máy cài Agent có bật, có mạng không.
2. Kiểm tra SQL Server (`MITACOSQL`) đang chạy.
3. Mở Agent → bấm **Đồng bộ ngay**.
4. Xem log Agent (thời gian, lỗi tiếng Việt).
5. Chưa được → gửi AI: ảnh log + thời điểm lỗi.

## 15.2 Web không vào được

1. Thử tải lại trang / trình duyệt khác.
2. Kiểm tra VPS còn chạy (hoặc Docker local `docker compose ps`).
3. Restart: `docker compose restart` (hoặc lệnh Chủ được cấp).
4. Xem `/health` còn xanh không.
5. Chưa được → gửi AI thông báo lỗi trên màn hình.

## 15.3 Tính lương lệch so với mong đợi

1. Kiểm tra kỳ lương: mẫu số (divisor) đúng chưa.
2. Kiểm tra công NV đó (worked_days, AL, REM) từ Chấm Công.
3. Kiểm tra mức đóng BHXH của NV (ảnh hưởng OT + BH).
4. Kiểm tra policy đang áp (mức chuyên cần, hệ số OT).
5. Dùng chức năng **đối chiếu** / gửi AI: MSNV + kỳ + số mong đợi.

## 15.4 Công nhân không xem được phiếu

1. Kiểm tra phiếu đã **Phát hành** chưa (status published).
2. Kiểm tra MSNV + mật khẩu công nhân.
3. Reset mật khẩu cho công nhân (HR).

## 15.5 Backup tự động & khôi phục

**Đăng ký backup hằng ngày (một lần khi Go-live):**

- Windows: `.\ops\register-backup-task.ps1` (mặc định 02:00)
- VPS Linux: `./ops/register-backup-cron.sh`

Kiểm tra thư mục `backups/` có file `djhrm_*.dump` mới; log: `backups/backup-task.log`.

**Khi hỏng dữ liệu:**

1. **Không thao tác thêm** để tránh ghi đè.
2. Báo AI ngay.
3. Dùng script restore trong `ops/` với bản backup gần nhất.
4. Kiểm tra lại dữ liệu sau khôi phục.

**Khóa kỳ nhầm:** Admin vào Tính Lương → **Mở khóa kỳ** (ghi hộp đen).

## 15.6 Đổi chính sách (mức chuyên cần, hệ số…)

1. Vào **Cấu Hình → Chính sách**.
2. Sửa số (ví dụ 230k → 630k), đặt ngày hiệu lực.
3. **Xác nhận 3 lần** khi lưu (tham số tiền).
4. Xem **Xem trước** trên 1 NV mẫu trước khi áp.

## 15.7 Nguyên tắc vàng khi sự cố

- Bình tĩnh, **không sửa DB tay**.
- Chụp màn hình + copy nguyên văn lỗi.
- Ghi lại: đang làm gì thì lỗi.
- Đưa AI xử lý (Chủ chỉ đạo, AI thực thi).

---

**Hết bộ Hiến pháp (00–15).**  
File 11–13 bắt buộc đọc trước khi code khung. File 14–15 tra cứu khi cần.
