# 02 — UI Portal, Phân quyền, Worker Portal

## 2.0 Luật thiết kế tối cao (bắt buộc)

Mọi Portal và màn Lv2–Lv4 tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**:

**Chính xác · Tiện dụng · Không rối mắt · Không chừa khoảng trống · Tận dụng không gian · Ngăn nắp · Gọn gàng · Đồng đều.**

- Portal 8 ô: tile **đồng đều**, lấp đủ lưới — không ô lệch, không dải trống vô nghĩa (vẫn **không** KPI trên Lv1 theo P5).
- Lv2+: full màn hình; nội dung **giãn theo breakpoint** — đặc biệt 1920×1080.
- Chi tiết pixel: `23_UI_MAN_HINH.md`.

## 2.1 Luật màn hình chính (BẮT BUỘC theo Chủ)

```
✅ CHỈ CÓ: Logo + lời chào user + lưới 8 ô (2×4 hoặc 4×2)
✅ Mỗi ô: icon + tên module (từ metadata)
✅ Click ô có quyền → vào Lv2 full màn hình
✅ Click ô KHÔNG có quyền → popup tiếng Việt (không ẩn / không mờ ô)
✅ Nút ← Portal luôn có ở mọi Lv2+

❌ KHÔNG sidebar
❌ KHÔNG KPI / bảng / chart trên Portal Lv1
❌ KHÔNG menu 3 cấp trên Portal
```

### Thông báo từ chối quyền (chuẩn)

```
COSMOS AI xin chào {Họ tên User}, bạn không có quyền truy cập.
Vui lòng liên hệ Admin.
```

## 2.2 Tám ô mặc định (Lv1) — seed metadata

| # | `key` | Tên hiển thị mặc định | Mô tả ngắn |
|---|-------|----------------------|------------|
| 1 | `overview` | Tổng Quan | Dashboard, biểu đồ, cảnh báo |
| 2 | `hr` | Nhân Sự | Hồ sơ NV, bộ phận, HĐ |
| 3 | `timekeeping` | Chấm Công | Công, trễ/sớm, sync Agent |
| 4 | `payroll` | Tính Lương | Kỳ lương, bảng lương, tính toán |
| 5 | `insurance` | Bảo Hiểm Thuế | BHXH/BHYT/BHTN (+ TNCN Phase 2) |
| 6 | `report` | Báo Cáo / KPI | Attendance, OT, Turnover |
| 7 | `dispute` | Khiếu Nại | Ticket CN, xử lý, AI rà soát |
| 8 | `config` | Cấu Hình | Policy, User, Agent, AI, Log — **chỉ Admin** |

> Tab 8 **Cấu Hình** có thể đổi tên/thứ tự/bật-tắt các ô Lv1 (metadata).  
> Seed mặc định phải khớp bảng trên khi cài mới.

## 2.3 Phân cấp màn hình Lv1 → Lv4

| Level | Ý nghĩa | UI |
|-------|---------|-----|
| **Lv1** | Portal 8 ô | Grid icon full màn |
| **Lv2** | Trong 1 module | Full màn, tab ngang hoặc card chức năng |
| **Lv3** | Chi tiết nghiệp vụ | Bảng AG-Grid / form |
| **Lv4** | Chi tiết 1 bản ghi | Panel / trang chi tiết NV / phiếu (log ngày, punch raw hiện ngay trong panel) |

> **Vừa đủ:** tối đa **4 cấp**. Không đào sâu Lv5 — dữ liệu raw (punch, log ngày) hiển thị ngay trong panel Lv4, tránh nesting rối.

**Mọi Lv2+ mở full màn hình.** Breadcrumb: `Portal › Tính Lương › Kỳ 10/2025 › MSNV 5290`.

## 2.4 Gợi ý Lv2 theo module (AI được tự thiết kế chi tiết bên trong)

### 1. Tổng Quan
- Card KPI: tổng NV, chuyên cần %, chi phí OT, số khiếu nại mở
- Biểu đồ HC / OT theo bộ phận (Chart.js hoặc Recharts)
- Danh sách cảnh báo gần đây (từ rule AI)

### 2. Nhân Sự
- AG-Grid danh sách NV (MSNV, họ tên, tổ, chức vụ, ngày vào, ngày ký HĐ, Lương HĐ, mức BHXH…)
- Import Excel / CRUD
- Hồ sơ Lv4

### 3. Chấm Công
- Bảng công tháng (ngày × NV hoặc tổng hợp)
- Danh sách trễ / về sớm
- Nút trạng thái Agent + “Đồng bộ ngay”
- Mapping bộ phận Mitapro ↔ DJ HRM

### 4. Tính Lương
- Chọn kỳ tháng
- [Đồng bộ công] → [Tính lương] → [Khóa kỳ]
- AG-Grid bảng lương (cột gần Excel thực tế)
- Xuất ATM / CASH
- Mở phiếu Lv4

### 5. Bảo Hiểm Thuế
- Mức đóng BH từng NV
- Báo cáo đóng BH tháng
- Placeholder TNCN (Phase 2)

### 6. Báo Cáo / KPI
- Attendance Rate, OT Rate, Turnover (công thức file Attendance 2026)
- Direct / Indirect manpower
- Export Excel

### 7. Khiếu Nại
- Inbox ticket (mới / đang xử lý / đóng)
- Chi tiết + lịch sử
- Nút “Rà soát bằng AI” (chỉ user có `ai_query`)

### 8. Cấu Hình (Admin only) — “tông xẹt tông” icon con

Các ô Lv2 bên trong Cấu Hình (cũng dạng icon grid nhỏ):

| Ô con | Chức năng |
|-------|-----------|
| Nhân sự / Lương | Công thức, phụ cấp catalog, mẫu số rule |
| Bảo hiểm thuế | Tỷ lệ BHXH/BHYT/BHTN, trần/sàn |
| Chấm công / Kỷ luật | Policy chuyên cần, trễ/sớm, giờ chuẩn |
| Lịch | Ngày lễ, tuần làm việc, auto mẫu số |
| User & Quyền | Tạo user, gán tối đa 7 module + `ai_query` |
| Agent Mitapro | Cấu hình sync, xem log |
| AI Gemini | API key, bật/tắt, hạn mức token/ngày |
| Portal Tabs | Thêm/xóa/đổi tên/thứ tự 8 ô Lv1 |
| Log / Hộp đen | Audit log cho AI & Admin |
| KPI (dự phòng) | Ngưỡng cảnh báo |

**Save tham số tiền:** xác nhận 3 lần (P10).

## 2.5 RBAC — Ma trận quyền

### Vai trò hệ thống

| Role | Module tối đa | Ghi chú |
|------|---------------|---------|
| `admin` | **8/8** bắt buộc | Chủ phần mềm |
| `user` | **Tối đa 7** module trong 8 ô | Do Admin gán |
| `worker` | Không vào Portal | Chỉ `/worker` |

### Quyền phụ (không phải ô Portal)

| Permission | Mã | Ai có |
|------------|-----|-------|
| Hỏi đáp / ra lệnh AI | `ai_query` | Admin gán thêm cho user tin cậy |
| Nhắc việc (badge) | tự động | Mọi user Web đã login — chỉ thấy việc thuộc phạm vi |

### Quy tắc gán quyền

1. Admin luôn có đủ 8 ô + `ai_query`
2. User thường: checkbox chọn các ô (max 7). Hệ thống **chặn** gán đủ 8
3. Ô `config` mặc định **không** gán cho user (chỉ Admin). Nếu sau này Admin cố gán — Hiến pháp khuyến cáo cấm; code enforce: `config` chỉ `role=admin`
4. Click ô không có quyền → popup (mục 2.1), **không** ẩn/mờ

## 2.6 Icon AI góc màn hình (Web nội bộ)

- Vị trí: góc dưới-phải hoặc trên-phải (cố định)
- Badge số = số việc chưa xử lý (rule-based, **0 token**)
- Click mở panel:
  - Tab **Việc cần làm** (mọi user Web)
  - Tab **Hỏi AI** (chỉ có `ai_query`)
- **Không** hiện trên Worker Portal

## 2.7 Worker Portal (`/worker`) — riêng biệt

### Không dùng lưới 8 ô

Chỉ các màn:

1. **Đăng nhập** — MSNV + mật khẩu (HR cấp; đổi mật khẩu lần đầu khuyến nghị)
2. **Trang chủ** — danh sách phiếu lương các tháng + trạng thái
3. **Chi tiết phiếu** — thực lãnh lớn; accordion thu nhập / khấu trừ
4. **Hành động**
   - `[Xác nhận đúng]` → khóa phiếu, không khiếu nại nữa
   - `[Khiếu nại]` → chọn lý do + ghi chú → gửi ticket (không AI)
5. **Tài khoản** — đổi mật khẩu, đăng xuất

### UX bắt buộc

- Font ≥ 16px, nút cao ≥ 48px
- PWA cài được lên màn hình điện thoại
- Không Gemini trên mobile công nhân

### Trạng thái phiếu

| Status | Ý nghĩa |
|--------|---------|
| `draft` | HR chưa phát hành |
| `published` | CN xem được, chưa xác nhận |
| `confirmed` | Đã xác nhận — **khóa** |
| `disputed` | Đang khiếu nại |
| `resolved` | HR đã xử lý (có thể republish nếu sửa) |
| `expired` | Hết hạn xác nhận (Admin cấu hình số ngày, mặc định 7) |

## 2.8 Design system tối thiểu

| Token | Giá trị |
|-------|---------|
| Font | Be Vietnam Pro |
| Primary | Navy `#1e40af` |
| Background | `#f8fafc` |
| Success / Warn / Danger | emerald / amber / red |
| Component | React + Tailwind (hoặc CSS module) — nhất quán |
| Bảng | **AG-Grid** (bắt buộc cho bảng lớn) |
| Tone Portal | Sáng, sạch, chuyên nghiệp — **không** hiệu ứng vũ trụ prototype |

---

## Thiết kế giao diện (luật tối cao)

Mọi Portal và màn Lv2–Lv4 tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.

*Tiếp: `03_CONG_THUC_LUONG.md`*
