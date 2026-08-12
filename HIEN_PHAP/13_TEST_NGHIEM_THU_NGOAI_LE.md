# 13 — Kiểm thử, Nghiệm thu, Ngoại lệ & Làm tròn

## 13.0 Nguồn chân lý & chiến lược đối chiếu — ĐÃ CHỐT

| Hạng mục | Quyết định |
|----------|------------|
| Phần mềm cũ | **GenuiSuite** (HRM Hàn Quốc) — tính lương công ty từ **~2015**, còn chạy nhưng chậm |
| File Excel lương | **Xuất từ GenuiSuite** (không phải gõ tay) — dùng để **học công thức & logic** |
| Chuẩn tính mới | **Decimal hiện đại, chính xác tuyệt đối** — **KHÔNG** bắt chước làm tròn lạc hậu của GenuiSuite |
| Vai trò GenuiSuite | Tham chiếu nghiệp vụ + đối chiếu regression; **không** phải chuẩn số phải khớp từng đồng |

**Nguyên tắc:** phần mềm mới lấy **đúng công thức** từ GenuiSuite/doc/Excel, nhưng dùng **công nghệ chính xác hơn** (Decimal, full-precision số ngày từ phút). Lệch vài đồng so với GenuiSuite = **bình thường và chấp nhận được** nếu giải thích được bằng quy tắc làm tròn.

## 13.1 Quy tắc làm tròn (chuẩn DJ HRM — không copy GenuiSuite)

| Hạng mục | Quy tắc seed (Admin có thể chỉnh) |
|----------|-----------------------------------|
| Kiểu số tiền | **`Decimal` / `NUMERIC` bắt buộc** — cấm `float` |
| Bước trung gian | Giữ `Decimal` độ chính xác cao (**không** làm tròn số ngày/giờ sớm) |
| Từng khoản hiển thị | Làm tròn **đồng** (0 lẻ) khi xuất phiếu |
| Thực lãnh | Làm tròn đồng |
| Giờ OT / công | Từ Mitapro (cho phép lẻ, ví dụ 26.8125) — **không** cắt 4 chữ số như GenuiSuite |
| Cách làm tròn | `ROUND_HALF_UP` |

Nguyên tắc: **tính bằng Decimal chính xác nhất; chỉ làm tròn ĐỒNG ở bước cuối/hiển thị.**

## 13.2 Kiểm thử (vừa đủ, tập trung chỗ dễ sai)

| Loại | Phạm vi |
|------|---------|
| Unit công thức | wd_salary, phụ cấp pro-rata, OT (base = SI + chuyên cần), BHXH/YT/TN, net — **toàn Decimal** |
| Regression GenuiSuite Excel | Kỳ **10/2025** trước (divisor 26), rồi 09/11/12 — **học logic**, phân loại lệch (xem 13.3) |
| Phân quyền | admin 8 ô, user max 7, ô không quyền → popup, config chỉ admin |
| Agent | Idempotent (gửi lại không trùng), retry |
| Worker | Xác nhận → khóa; khiếu nại tạo ticket |
| Backup | Restore thử ra được DB |

Không cần phủ 100% test cho mọi thứ — **ưu tiên tiền lương & quyền**.

## 13.3 Tiêu chí nghiệm thu tính lương

| Loại chênh so GenuiSuite | Mức | Kết luận |
|--------------------------|-----|----------|
| **A — Làm tròn cũ** (vài → vài chục đồng; do GenuiSuite cắt số ngày 4 chữ số) | Nhỏ | **Chấp nhận** — DJ HRM đúng hơn; ghi log giải thích |
| **B — Công thức / logic sai** | Bất kỳ | **Không chấp nhận** — phải sửa engine |
| **C — Ngoại lệ nghiệp vụ** (vd REM được trả) | Lớn | **HR xác nhận** quy tắc → cấu hình policy, không bịa |

| Field | Mục tiêu |
|-------|----------|
| Công thức (WD, OT base, BH, gross, net) | Khớp **logic** GenuiSuite 100% |
| Số tiền từng đồng vs Excel cũ | **Không bắt buộc** khớp tuyệt đối nếu thuộc nhóm A |
| Tổng công / giờ OT | Khớp nguồn Mitapro |
| nội bộ DJ HRM | Tính lại 2 lần cùng input → **0đ lệch** (idempotent Decimal) |

Đạt khi: mọi lệch so GenuiSuite được **phân loại A/B/C**; nhóm B = 0; nhóm C đã chốt với HR.

## 13.4 Ma trận ngoại lệ nghiệp vụ (phải xử lý / hoặc ghi nhận)

| Ngoại lệ | Cách xử lý |
|----------|-----------|
| Vào làm giữa tháng | Tính theo worked_days thực; thử việc theo ngày ký HĐ |
| Nghỉ việc giữa tháng | Chốt công tới ngày nghỉ |
| Đổi lương / bộ phận giữa tháng | Ghi mốc hiệu lực; tách đoạn nếu cần (Phase sau nếu hiếm) |
| Ký HĐ giữa tháng | Trước ngày ký = lương thử việc, sau = lương HĐ |
| Thiếu punch / quên chấm | Cờ cảnh báo cho HR sửa tay; không tự bịa |
| Ca qua ngày / làm đêm | Theo lịch + rule OT đêm |
| OT lễ trùng Chủ nhật | Áp hệ số cao hơn (policy) |
| Nghỉ phép nửa ngày | worked_days lẻ (0.5) |
| BHXH bắt đầu/ngừng giữa tháng | Cờ `si_enrolled` + mức đóng theo kỳ |
| NV CASH mới, BH = 0 | Khớp sheet CASH Excel |

MVP: xử lý các case phổ biến; case hiếm → cho HR chỉnh tay + ghi log, không code phức tạp vội (P11).

## 13.5 Dữ liệu test

- Dùng **dữ liệu ẩn danh** trong dev (che tên/CCCD/STK).
- Không đưa lương thật của NV lên môi trường dev/chia sẻ.
- Fixture neo: 5 NV Oct/2025 (`1514, 1643, 5290, 5321, 1732`).

## 13.6 Nhật ký regression test (cập nhật phiên)

| Ngày | API pytest | Ghi chú |
|------|------------|---------|
| 2026-08-12 | **346 pass / 0 fail** | Sửa 7 test chấm công lệch `ot_split` (grace 17:15); chi tiết **`BAO_CAO_BUG_FAIL_20260812_PM.md`** |

**Quy tắc OT trong test (phải khớp engine):**
- Ra **≤ 17:15** → `ot_minutes = 0` (grace toilet).
- Ra **> 17:15** → OT tính từ **17:00**; **Thứ 3 / Thứ 5** → cột OT trên sổ; ngày khác → `OT_EXT`.
- Một lần bấm sáng sau dedupe 60s → ghi **`first_in`**, không bỏ trống cả hai cột.

*Tiếp: `14_DATA_DICTIONARY.md`*
