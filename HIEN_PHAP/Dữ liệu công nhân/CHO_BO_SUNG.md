# Chờ bổ sung — hồ sơ công nhân trên web

> **Ghi nhận:** 2026-08-13 · HR sẽ bổ sung dữ liệu tiếp.

## Vùng trống trên màn hồ sơ NV

Overlay **Hồ sơ nhân viên** (full screen) — các tab/ cột:

| Phần | Trạng thái | Ghi chú |
|------|------------|---------|
| Công việc | Một phần | Tổ, chức vụ, ngày vào — thường đã có |
| Lương | Một phần | Lương HĐ, phụ cấp — thường đã có |
| **Cá nhân** | Đã nạp 14.08 | GT, NS, SĐT, hôn nhân, số con, trình độ; dân tộc Kinh / tôn giáo Không |
| **Cư trú & giấy tờ** | Một phần | Quốc tịch VN; địa chỉ, CCCD thường đã có |
| **Bảo hiểm & Ngân hàng** | Một phần | TK NH thường có; sổ BHXH hay thiếu |

Mở NV trên web → vùng giữa **Cá nhân / Cư trú** có thể **trống** vì DB chưa nhập — **không phải lỗi layout**, chờ HR điền.

## Vùng trống lớn — cột Lương / «Phụ cấp» (form Thêm + khối list)

> **Ghi nhận thêm:** 2026-08-13 — HR hỏi «chỗ này trống, dùng làm gì?»

**Là gì:** Trong overlay hồ sơ, cột **Công việc** có form **Thêm phụ cấp** (Loại · Số tiền · nút **Thêm**). Cột **Lương** có khối **Phụ cấp** (danh sách đã gán). CSS căn 3 cột đầu cùng chiều cao → khi danh sách phụ cấp **ít hoặc trống**, khối list **giãn cao** → nhìn như ô trống lớn (đường chéo thường là góc resize / vùng scroll trống, **chưa phải biểu đồ**).

**Hiện trạng:** Chưa gán widget — chỉ list phụ cấp + placeholder «Chưa có gán phụ cấp».

### Có thể dùng vùng này để (đề xuất — chưa làm)

| Ưu tiên | Ý tưởng | Nguồn dữ liệu sẵn có |
|--------|---------|----------------------|
| ★★★ | **Sparkline lương thực lãnh 6–7 tháng** (Jan–July 2026) | `sources.salary_by_month` trong JSON / file `HIEN_PHAP/Salary/*.xls` |
| ★★★ | **Tóm tắt thu nhập tháng gần nhất** — Gross, Net, PC, OT | Cùng file lương |
| ★★ | **Lịch sử điều chỉnh lương HĐ** | API `GET /employees/{id}/salary-history` |
| ★★ | **Cột phụ cấp chi tiết** — Chuyên cần, Đi lại, Độc hại… (tháng gần nhất) | Bảng lương GenusSuite |
| ★ | **Thâm niên + loại HĐ** (chỉ text, không chart) | Đã có trên API employee |
| ★ | **Thu gọn layout** — bỏ giãn cao khi list PC trống (chỉ fix UI) | CSS |

**Không nên:** nhập thêm hồ sơ cá nhân (SĐT, CCCD…) vào đây — thuộc cột **Cá nhân / Cư trú**.

### Việc kỹ thuật (khi HR chọn hướng)

- [ ] Quyết định: biểu đồ lương **hay** chỉ thu gọn ô trống
- [ ] Nếu biểu đồ: API hoặc đọc `salary_by_month` từ snapshot khi mở hồ sơ
- [ ] (Tuỳ chọn) Thu gọn `.emp-allow-list-block` khi `allowances.length === 0`

## Thống kê từ file JSON (454 NV)

Nguồn bổ sung 14.08 (`Thông tin bổ sung  14.08.26.xlsx`) đã nạp vào JSON:

| Trường | Sau bổ sung 14.08 |
|--------|-------------------|
| Hôn nhân | **354/454** (256 đã kết hôn, 98 độc thân) |
| Có con | **175** NV |
| Điện thoại | **358/454** |
| Quốc tịch Việt Nam / dân tộc Kinh / tôn giáo Không | **451/454** (bỏ NV test) |
| Trình độ (sheet 02 cột M) | **350/454** |
| Phụ cấp sheet 03 | Chuyên cần + đi lại ~354; tay nghề 188; độc hại; chức vụ 44; HSE/PCCC tách |

MSNV **8852** có trong Excel nhưng chưa có file JSON snapshot local.

## Nguồn bổ sung

1. **`Thông tin bổ sung  14.08.26.xlsx`** (thư mục này) — hôn nhân, số con, STK, SĐT, hồ sơ sheet 02.
2. **`HIEN_PHAP/Thông tin danh sách nhân viên/`** — GenusSuite 14.08 + ảnh.
3. **Nhập tay** trên web: liên hệ khẩn (nếu có).

## Việc kỹ thuật (sau khi HR có dữ liệu)

- [x] Nạp hôn nhân / số con / SĐT từ Excel 14.08
- [x] Quốc tịch Việt Nam, dân tộc Kinh, tôn giáo Không
- [x] Trình độ học vấn sheet 02 cột M
- [x] Phụ cấp sheet 03 (PCCC/HSE, chức vụ, độc hại, chuyên cần, đi lại, tay nghề, khác)
- [ ] Liên hệ khẩn — chờ HR

## NV test — bỏ qua khi bổ sung

`1604`, `1718`, `8851` — dữ liệu giả UAT.
