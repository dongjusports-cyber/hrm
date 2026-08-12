# 05 — AI Gemini (COSMOS AI)

## 5.1 Tên & tính cách

- Tên hiển thị: **COSMOS AI**
- Xưng hô: gọi **họ tên user** đã tạo
- Ngôn ngữ: Tiếng Việt
- Quyền với dữ liệu: **CHỈ ĐỌC** — không sửa lương, không đổi policy, không xóa

## 5.2 Nguồn API

| Hạng mục | Giá trị |
|----------|---------|
| Provider | **Google Gemini Pro** |
| Key | Công ty mua Google Workspace / Gmail → Admin dán API Key trong Cấu Hình → AI |
| Model mặc định | Gemini Pro (Admin chọn được Flash nếu muốn rẻ hơn) |
| Lưu key | Mã hóa at-rest; không commit vào git |

## 5.3 Hai lớp AI (tối ưu token)

### Lớp A — Nhắc việc (Rule Engine) — **0 token API**

Icon góc Web + badge số. Trigger ví dụ (Admin cấu hình ngưỡng):

| Sự kiện | Người nhận gợi ý |
|---------|------------------|
| Công nhân gửi khiếu nại mới | User có quyền `dispute` / `payroll` |
| Khiếu nại > 24h chưa xử lý | NV tính lương |
| Phiếu published chưa xác nhận > N ngày | NV tính lương |
| Agent sync lỗi | Admin |
| Kỳ lương chưa khóa quá hạn | NV tính lương |
| OT bộ phận vượt ngưỡng | Admin / report |

**Công nhân khiếu nại → AI không chat với CN.**  
Chỉ tạo ticket + **nhắc NV tính lương** trên badge.

### Lớp B — Hỏi đáp / ra lệnh (Gemini) — **tốn token có kiểm soát**

- Chỉ user có permission **`ai_query`**
- Chỉ gọi API khi user **bấm Gửi** trong panel AI
- Use case chính: *“Rà soát khiếu nại #K001”*, tìm dữ liệu, giải thích lệch công/OT
- Admin có thể hỏi tổng quan (read-only)

## 5.4 Việc AI KHÔNG được làm

- ❌ Xuất hiện trên Worker Portal / điện thoại công nhân  
- ❌ Tự xác nhận / từ chối khiếu nại  
- ❌ Tự sửa số liệu lương  
- ❌ Tự đổi policy  
- ❌ Quét nền hàng giờ bằng LLM (tránh tốn tiền)

## 5.5 Prompt contract (khi gọi Gemini)

System prompt tối thiểu phải gồm:

1. Vai trò: trợ lý HRM DONGJU, tiếng Việt, read-only  
2. Context: MSNV, kỳ lương, snapshot phiếu, số lần trễ/sớm, giờ OT, policy_version  
3. Lệnh: chỉ phân tích & đề xuất; nếu cần sửa → bảo user liên hệ HR  
4. Không bịa số — thiếu dữ liệu thì nói thiếu  

Giới hạn:

| Tham số | Seed |
|---------|------|
| Max câu / user / ngày | 20 (Admin) |
| Max token / response | cấu hình |
| Bật/tắt toàn cục | Cấu Hình → AI |

## 5.6 Giám sát lỗi phần mềm — **SAU MVP (Phase 2), không làm ngay**

> Vừa đủ: MVP chỉ cần Lớp A (nhắc việc) + Lớp B (rà khiếu nại). Giám sát phần mềm bằng AI để **sau khi hệ thống chạy ổn định**.

- Log lỗi backend → hàng đợi  
- Rule hoặc Gemini tóm tắt cho Admin: “Lỗi sync 3 lần, đề xuất kiểm tra Agent”  
- Không tự patch production

## 5.7 Ước chi phí

| Chế độ | Chi phí |
|--------|---------|
| Chỉ nhắc việc (rule) | **0đ** |
| + Gemini khiếu nại ~10–20 ticket/tháng | Thấp (dùng Gemini Pro Workspace) |
| Tắt chat AI | **0đ** API |

*Tiếp: `06_CONG_NGHE_KIENTRUC.md`*
