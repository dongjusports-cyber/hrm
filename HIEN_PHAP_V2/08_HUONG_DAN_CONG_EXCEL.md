# 08 — Hướng dẫn HR: lấy công · tải về máy · sửa · đưa lại hệ thống

> **Đối tượng:** HR pilot UAT · **URL:** `http://192.168.1.123:5173`  
> **Tài khoản:** `hr1` / `hr2` / `hr.demo`  
> **Ngày:** 2026-08-13

---

## Bảng tổng quan — 4 việc HR hay làm

| # | Việc | Làm ở đâu trên web | Có nút «Tải Excel» cả tháng? |
|---|------|---------------------|-------------------------------|
| **1** | **Lấy công** từ máy vân tay | Chấm Công → tab **Đồng bộ** | Không — dữ liệu vào hệ thống qua Agent |
| **2** | **Xem / copy** công ra Excel máy | Tab **Tổng hợp** · **Bảng ngày** | **Chưa có** xuất file cả tháng — xem mục 3 |
| **3** | **Sửa công** trên web | Tab **Tổng hợp → Xem** · **Bảng ngày** · **Rà soát** | — |
| **4** | **Đưa công đã sửa** vào hệ thống | Sửa trực tiếp web **hoặc** dán Excel (1 ngày) | Dán từ Excel — mục 5 |

---

## 1 — Lấy công (Mitapro → DJ HRM)

| Bước | Thao tác | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Portal → **Chấm Công** | Mở module |
| 2 | Chọn **Kỳ** (vd. `2026-08`) | Thanh trên cùng |
| 3 | Tab **Đồng bộ** | Panel Agent Mitapro |
| 4 | Bấm **Đồng bộ ngay** (menu **⋯** trên toolbar cũng có) | Log: trạng thái success |
| 5 | Tab **Tổng hợp** → **Làm mới** | Bảng NV có công / OT |

**Lưu ý:** Agent chạy nền trên máy `.122` (IT đã cài). HR không cần mở Mitapro — chỉ bấm đồng bộ trên web.

---

## 2 — Tải / copy công về máy (Excel)

| Cách | Làm thế nào | Phù hợp khi |
|------|-------------|-------------|
| **A. So sánh Genus** | Dùng file Excel lương/công GenusSuite sẵn có (`HIEN_PHAP/Salary/…`) | Đối chiếu UAT với số cũ |
| **B. Copy từ web** | Tab **Bảng ngày** → chọn vùng lưới → `Ctrl+C` → dán vào Excel | Lấy **1 ngày** cả xưởng |
| **C. Copy từng NV** | Tab **Tổng hợp** → **Xem** → chụp màn / copy tay cột Vào/Ra | Rà **1 MSNV** cả tháng |
| **D. Xuất Excel hệ thống** | *(Chưa có trong bản UAT)* | Ghi backlog — liên hệ IT nếu cần gấp |

> **Thật:** DJ HRM UAT **chưa có** nút «Xuất bảng công tháng .xlsx». HR sửa công **trên web** hoặc **dán lại** (mục 5). Riêng **OT ngoài (ATM)** có xuất Excel: menu **⋯ → OT ngoài**.

---

## 3 — Sửa công trên web (khuyến nghị UAT)

### 3a. Một nhân viên — cả tháng

| Bước | Thao tác | Ghi chú |
|------|----------|---------|
| 1 | Tab **Tổng hợp** → tìm MSNV → bấm **Xem** | Mở sheet chi tiết |
| 2 | Cột **Vào** / **Ra** — bấm ô → gõ **24h** `HH:mm` (vd. `07:53`, `17:15`) | Gõ `1240` → thành `12:40` |
| 3 | **Enter** hoặc **Tab** | Tự lưu (cần **đủ Vào và Ra**) |
| 4 | **Esc** trong ô | Hoàn tác — **không** thoát sheet |
| 5 | Hoặc dùng thanh **Lưu giờ** dưới bảng | Chọn ngày + Vào/Ra + Lưu |

### 3b. Cả xưởng — một ngày

| Bước | Thao tác | Ghi chú |
|------|----------|---------|
| 1 | Tab **Bảng ngày** | Chọn **Ngày công** |
| 2 | Bấm **1 lần** cột **Vào** hoặc **Ra** | Sửa trực tiếp trên lưới |
| 3 | Hoặc tick NV → nhập giờ bulk → **Đặt giờ Vào/Ra** | Nhiều NV cùng giờ |
| 4 | **Gán nghỉ** / mã nghỉ | Chọn NV → mã ALE, OFF… |

### 3c. Thiếu chấm / trễ sớm

| Bước | Thao tác |
|------|----------|
| 1 | Tab **Rà soát** — danh sách cảnh báo |
| 2 | Bấm dòng → form **Vào/Ra** → **Lưu giờ tay** |

---

## 4 — Sau khi sửa: tổng hợp lại

| Bước | Thao tác | Khi nào bắt buộc |
|------|----------|------------------|
| 1 | Menu **⋯ → Tổng hợp công** | Sau khi sửa nhiều dòng / dán Excel |
| 2 | Kiểm tab **Tổng hợp** — cột Công, OT, Trễ | Trước khi sang **Tính Lương** |

**Kỳ đã khóa:** chỉ xem — không sửa, không dán.

---

## 5 — Sửa trên Excel máy rồi đưa lại (dán 1 ngày)

Dùng khi HR quen sửa hàng loạt trên Excel **cho cùng một ngày**.

### Chuẩn bị file Excel (3 cột)

| Cột A | Cột B | Cột C |
|-------|-------|-------|
| **MSNV** | **Vào** | **Ra** |
| 1519 | 07:48 | 17:02 |
| 1604 | 08:01 | 17:15 |

- Giờ **24h** `HH:mm`  
- Copy **cả khối** (có tab giữa cột)

### Dán vào web

| Bước | Thao tác |
|------|----------|
| 1 | Tab **Bảng ngày** → chọn đúng **Ngày công** |
| 2 | Click vào vùng lưới (không cần chọn ô) |
| 3 | `Ctrl+V` | 
| 4 | Thông báo: «Đã dán N dòng (MSNV · Vào · Ra)» |
| 5 | **⋯ → Tổng hợp công** |

**Không hỗ trợ:** dán **cả tháng** một lần — mỗi lần dán = **một ngày**.

---

## 6 — Bảng tra nhanh tab Chấm Công

| Tab | HR dùng để |
|-----|------------|
| **Tổng hợp** | Xem cả tháng · **Xem** chi tiết 1 NV · sửa từng ngày |
| **Bảng ngày** | Sửa **1 ngày** cả xưởng · **dán Excel** |
| **Rà soát** | Sửa thiếu chấm / bất thường |
| **Phép** | Duyệt đơn Worker |
| **Trễ / sớm** | Danh sách vi phạm kỳ |
| **Điều chỉnh** | Ghi nghỉ / OT cả tháng (1 MSNV) |
| **Đồng bộ** | Mitapro · log Agent |

---

## 7 — Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Xử lý |
|-------------|-------------|--------|
| Dán Excel không ăn | Sai định dạng / thiếu tab | Đúng 3 cột MSNV · Vào · Ra |
| Lưu giờ báo lỗi | Thiếu Vào hoặc Ra | Nhập đủ 2 cột |
| Không sửa được | Kỳ **locked** | Liên hệ Admin mở kỳ |
| Công vẫn 0 sau sync | Agent / map MSNV | Tab Đồng bộ · IT kiểm `.122` |
| NV nghỉ trước kỳ vẫn hiện | Dòng cũ | **⋯ → Tổng hợp công** (IT đã fix loại NV nghỉ) |

---

## 8 — Việc chưa có (backlog)

| Tính năng | Trạng thái |
|-----------|------------|
| Xuất Excel **bảng công cả tháng** (.xlsx) | Chưa — ghi `_TOI_UU/` nếu cần |
| Import Excel **cả tháng** một file | Chưa — chỉ **dán 1 ngày** |
| Sửa công trên Excel rồi upload file | Chưa — dùng **dán** hoặc **sửa web** |

---

*Liên quan: [`07_UAT_HR_1_THANG.md`](./07_UAT_HR_1_THANG.md) · [`04_CHAM_CONG_AGENT.md`](../HIEN_PHAP/04_CHAM_CONG_AGENT.md)*
