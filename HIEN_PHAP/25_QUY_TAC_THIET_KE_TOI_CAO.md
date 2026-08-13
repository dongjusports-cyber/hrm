# 25 — QUY TẮC THIẾT KẾ TỐI CAO (LUẬT BẮT BUỘC)

> **Trạng thái:** Hiện hành · **Ưu tiên ngang P11** (KISS) khi làm giao diện  
> **Áp dụng:** Mọi màn Lv2–Lv4 · Portal · Worker · UI V1 (5173) và UI V2 (5174)  
> **Chi tiết pixel:** bổ sung tại `23_UI_MAN_HINH.md` — file này là **nguyên tắc tối cao**, không được vi phạm

---

## 25.0 Tám chữ vàng (bắt buộc — Chủ chốt 2026-08-13)

Mọi quyết định layout, kích thước, khoảng cách, cột lưới, ảnh, form **phải** đạt đủ **cả tám**:

| # | Nguyên tắc | Nghĩa | Không được |
|---|------------|-------|------------|
| **D1** | **Chính xác** | Số, nhãn, trạng thái, đơn vị đúng nghiệp vụ; căn lề đúng loại dữ liệu (tiền phải phải, mã tabular) | Sai số, nhãn mơ hồ, cột lệch kiểu |
| **D2** | **Tiện dụng** | Làm xong việc với ít thao tác; nút hay dùng trong tầm tay; phím tắt khi lưới dày | Trang trí mà không giúp HR/Kế toán làm nhanh hơn |
| **D3** | **Không rối mắt** | Một vùng một việc; không chồng chéo màu/nút; không quá 12 trường một tab form (§23.3) | Nhồi nhét, nhiều viền/đổ bóng, chữ nhỏ chen chúc |
| **D4** | **Không chừa khoảng trống** | Không để dải trắng lớn hai bên, góc chết, toolbar `fit-content` lơ lửng giữa màn | Căn giữa khối nhỏ trên màn 1920×1080 khi còn chỗ dùng |
| **D5** | **Tận dụng không gian trống** | Giãn cột đều, ảnh/ô nhập lớn hơn trên màn rộng; breakpoint 1400 / 1680 / 1920 | Một kích thước cố định cho mọi độ phân giải |
| **D6** | **Ngăn nắp** | Cùng loại nội dung cùng vùng; header / toolbar / dữ liệu / status tách rõ (§23.1) | Trộn lẫn lọc, tab, và form trong một khối không ranh giới |
| **D7** | **Gọn gàng** | Padding đồng bộ; hàng thẳng; không wrap toolbar khi còn cách gom (§23.1) | Lệch 2–4px giữa các cột; tab xuống dòng trên màn đủ rộng |
| **D8** | **Đồng đều** | Cột lưới cùng bề rộng khi có thể; khoảng cách gap nhất quán; typography một cấp trong cùng vùng | Cột 4–5 hẹp hơn cột 1–3 vô lý; font nhảy size ngẫu nhiên |

> **Cân bằng D3 ↔ D4–D5:** Tận dụng không gian **không** có nghĩa nhồi thêm cột/nút.  
> Cách đúng: **phóng to** nội dung đang có (ảnh NV, ô nhập, chữ đọc được), **giãn đều** lưới, **kéo dài** toolbar — không thêm widget trang trí.

---

## 25.1 Quy tắc vận hành (AI & dev bắt buộc áp dụng)

### R1 — Màn chuẩn tham chiếu
Thiết kế và nghiệm thu layout trên **1920×1080** (chuẩn nhà máy). Phải vẫn ổn trên **1366×768** (gọn) — không được phá D3–D7 ở màn nhỏ chỉ để “đẹp” màn lớn.

### R2 — Không gian ngang
| Vùng | Quy tắc |
|------|---------|
| Header / identity | Ảnh hoặc avatar **trái**, thông tin + hành động **phải**, khối phải `width: 100%` |
| Toolbar | **Full width** trong vùng nội dung; không `fit-content` / `max-content` trừ chip lọc |
| Lưới form nhiều cột | ≥1680px: cột **bằng nhau** (`repeat(n, 1fr)`) trừ khi có lý do nghiệp vụ (cột MSNV hẹp) |
| Full-screen sheet | Dùng hết chiều ngang viewport; padding tăng theo breakpoint, không khối 1120px lơ lửng giữa màn |

### R3 — Không gian dọc
- Chrome cố định theo §23.1 (160px) — **một** vùng cuộn dữ liệu.
- Form hồ sơ: ưu tiên **một trang không cuộn** trên tab chính khi ≤12 trường/nhóm (đã chốt FullScreenSheet).
- Ảnh nhân viên: tỷ lệ **3:4** hoặc **4:5**; scale theo breakpoint (vd. 120×150 → 180×225 @1920).

### R4 — Đồng đều
- Gap lưới: 8–14px (compact) · 12–18px (màn rộng) — **một giá trị trong cùng màn**.
- Nhãn trường: luôn **trên** ô (§23.3), cùng cỡ trong cùng form.
- Nút cùng hàng: cùng chiều cao (`btn-sm` / `btn-primary` thống nhất).

### R5 — Chính xác hiển thị
- Tiền: `tabular-nums`, canh phải, không hiện 0 (§23.2).
- Rỗng: gạch mờ — không để ô trắng vô nghĩa chiếm chỗ.
- Trạng thái / mã màu: đúng lookup, không tự đặt tên.

### R6 — Tiện dụng
- Mọi lưới HR/Lương/Công: chọn nhiều + thanh hành động (§23.5).
- Phím tắt: `/`, `Ctrl+K`, `F2`, `Esc` — không che bởi FAB (§23.11 U1 Done).
- Double-click / Xem mở hồ sơ — không bắt user đi 4 cấp menu.

---

## 25.2 Breakpoint bắt buộc (web)

| Breakpoint | Hành vi layout |
|------------|----------------|
| ≤768px | 1–2 cột form; ảnh NV thu nhỏ; ưu tiên đọc được |
| ≤1366px | Toolbar **không wrap**; lọc thừa vào «Lọc nâng cao» |
| ≥1400px | Tăng padding vùng nội dung; ảnh / field lớn hơn một bậc |
| ≥1680px | Lưới form 5 cột đều (nếu màn có 5 nhóm); font field +1 bậc |
| ≥1920px | Tận dụng full width; ảnh NV max ~180×225; không còn dải trống hai bên header |

---

## 25.3 Checklist trước khi merge UI

AI / dev **phải** tự trả lời **Có** cho tất cả:

- [ ] **D1–D8:** Màn đạt đủ tám nguyên tắc?
- [ ] Màn 1920×1080: không còn khối nội dung bé lơ lửng giữa với khoảng trống lớn hai bên?
- [ ] Toolbar / header kéo full width?
- [ ] Cột lưới form đồng đều trên màn rộng?
- [ ] Không thêm cuộn ngang (§23 mục tiêu)?
- [ ] Không vi phạm P11 (KISS) — không thêm thư viện / animation chỉ để lấp chỗ trống?

---

## 25.4 Ví dụ đã chốt (tham chiếu)

| Màn | Áp dụng |
|-----|---------|
| **Hồ sơ NV (FullScreenSheet)** | Ảnh trái; MSNV + Họ tên + toolbar phải full width; 5 cột đều @1680+; ảnh 180×225 @1920 |
| **Danh sách NV** | MSNV + Họ tên ghim trái; status bar đếm bản ghi; toolbar ≤46px |
| **Portal 8 ô** | Không KPI trên Lv1 (P5) — nhưng tile **đồng đều**, lấp đủ lưới, không ô lệch |

---

## 25.5 Cấm (anti-pattern)

| Cấm | Lý do |
|-----|-------|
| Căn giữa form hẹp trên màn 1920 | Vi phạm D4, D5 |
| `width: fit-content` cho toolbar / header-main khi còn chỗ ngang | Vi phạm D4, D7 |
| Thêm cột trang trí / card rỗng để “đầy màn” | Vi phạm D3 |
| 5 cột nhưng 2 cột cuối hẹp vô lý | Vi phạm D8 |
| Font/ảnh một cỡ mọi breakpoint | Vi phạm D5 trên màn lớn |
| Bỏ qua §23.1 chrome 160px để “thêm chỗ” | Phá cấu trúc ngăn nắp (D6) |

---

## 25.6 Tham chiếu chéo

| File | Liên quan |
|------|-----------|
| `01_VISION_NGUYEN_TAC.md` | **P12** — tóm tắt tám chữ vàng |
| `02_UI_PORTAL_PHAN_QUYEN.md` | Portal & phân cấp Lv1–Lv4 |
| `23_UI_MAN_HINH.md` | Pixel, chrome, lưới, form |
| `HIEN_PHAP_V2/03_STACK_UI_V2.md` | Token & stack UI V2 |
| `HIEN_PHAP_V2/06_QUY_TAC_CHO_AI.md` | Workflow AI — bắt đọc file này khi sửa UI |

---

*Mọi file Hiến pháp khác (03–24, V2/00–08) đều phải tuân file này khi có phần hiển thị cho người dùng.*
