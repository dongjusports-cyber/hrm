# 23 — GIAO DIỆN VÀ MÀN HÌNH

> Mục tiêu không phải "không bao giờ cuộn" mà là **"làm xong một việc không cần cuộn"**.
> Cuộn dọc theo số nhân viên là vật lý. Cuộn ngang là thứ phải xóa bằng được.

---

## 23.1 NGÂN SÁCH CHIỀU CAO — áp cho mọi màn

| Dải | Cao | Hành vi | Nội dung |
|-----|-----|---------|----------|
| Thanh module | 44px | Cố định | Breadcrumb, tên màn, **tối đa 3** nút hành động |
| Sub-tabs | 38px | Cố định | **Tối đa 6** tab, gạch chân màu nhấn |
| Toolbar lọc | 46px | Cố định, **KHÔNG xuống dòng** | Tối đa 4 bộ lọc hay dùng + ô tìm |
| Vùng dữ liệu | phần còn lại | **Cuộn duy nhất** | Lưới hoặc form |
| Status bar | 32px | Cố định | Đếm bản ghi, cảnh báo, chế độ xem |

**Tổng chrome cố định = 160px.** Vùng dữ liệu = `calc(100vh - 160px)`.

| Màn hình | Tầng | Cao dòng | Số dòng thấy |
|----------|------|----------|--------------|
| 1366×768 | Gọn (chrome 134px) | 28px | ~18 |
| 1920×1080 | Chuẩn | 32px | ~24 |
| 2560×1440 | Thoáng | 36px | ~31 |

> ⚠️ **Toolbar tuyệt đối không được xuống dòng.** Trên màn 1366 mà để 6 bộ lọc tự xuống hàng thì
> chrome thành 206px và lưới mất 4 dòng. Bộ lọc thứ 5 trở đi nằm sau nút **Lọc nâng cao** mở ra
> khung trượt. Điều kiện đang bật hiện thành chip ngay trong hàng đó; chip tràn thì thu thành
> "+3 điều kiện".

---

## 23.2 QUY ƯỚC LƯỚI DỮ LIỆU

### Cột
| Quy ước | Chi tiết |
|---------|----------|
| Ghim trái | MSNV + Họ tên ở **mọi** lưới nhân sự |
| Ghim phải | Thực lãnh ở lưới bảng lương |
| Nhóm thu gọn | Phụ cấp, Tăng ca, Nghỉ — mặc định chỉ hiện cột tổng |
| Cột tiền | Canh phải, `font-variant-numeric: tabular-nums`, **không hiện số 0** |
| Giá trị rỗng | Dấu gạch mờ, để mắt chỉ bắt vào ô có số |
| Bộ phận › Tổ | **Luôn đi cùng nhau** — tên tổ bị trùng giữa các bộ phận |

### Phím tắt
| Phím | Tác dụng |
|------|----------|
| `↑` `↓` | Đổi dòng, khung chi tiết cập nhật theo |
| `F2` | Sửa tại chỗ kiểu Excel |
| `Ctrl+Enter` | Lưu và xuống dòng kế |
| `Ctrl+V` | Dán khối từ Excel vào lưới |
| `/` | Nhảy vào ô tìm kiếm |
| `Ctrl+K` | Bảng lệnh — gõ tên màn hoặc MSNV để đi thẳng |

### Khung chi tiết
Trên **1800px**: chia đôi cố định, chi tiết bên phải rộng 380px.
Dưới ngưỡng đó: khung chi tiết **trượt đè** lên lưới, đóng bằng `Esc`.
Cố chia đôi trên màn 1366 thì cả hai bên đều chật, lại đẻ ra đúng cái cuộn ngang cần tránh.

---

## 23.3 QUY ƯỚC TRƯỜNG TRONG FORM

| Quy ước | Chi tiết |
|---------|----------|
| Số trường mỗi tab | **Tối đa 12**, xếp 3 cột — quá thì tách tab, không cho cuộn dọc |
| Nhãn | 10,5px **phía trên** ô (không đặt bên trái, để cột thẳng hàng) |
| Ô chọn | Mọi mã lấy từ danh mục Admin, **không gõ tự do** |
| Ngày | Kiểu `date` thật, có lịch bật ra |
| Tiền | Tự chấm phân cách nghìn khi rời ô, canh phải |
| Bắt buộc | Đánh dấu **ngay lúc nhập**, không đợi bấm Lưu |
| Chỉ đọc | Trường suy ra (thâm niên, tuổi, số dư phép) hiện mờ, không cho sửa |

---

## 23.4 BA MƯƠI MÀN HÌNH

### Module NHÂN SỰ — 7 màn

| Tab | Kiểu | Nội dung |
|-----|------|----------|
| **Danh sách** | lưới | Ghim MSNV + Họ tên. Cột: Bộ phận › Tổ, Chức vụ, Ngày vào, Thâm niên, Loại HĐ, Lương HĐ, Trạng thái, Tài khoản. Nhóm thu gọn: Hồ sơ cá nhân (6), Bảo hiểm (4) |
| **Hồ sơ chi tiết** | form | 6 tab cấp 3: Cá nhân · Cư trú & giấy tờ · Bảo hiểm · Công việc · Lương & phụ cấp · Kinh nghiệm |
| **Hợp đồng** | chia đôi | Trái: HĐ hết hạn trong 60 ngày, sắp theo ngày hết hạn tăng dần. Phải: dòng thời gian HĐ của người đang chọn, nút ký tiếp |
| **Thân nhân & giảm trừ** | chia đôi | Lưới người phụ thuộc kèm khoảng hiệu lực. Cột tự tính: số người phụ thuộc đang hiệu lực trong kỳ lương đang mở |
| **Biến động** | lưới | Hợp nhất `employee_assignments` + `employee_salary_history` + `employee_violations`. Mỗi dòng có giá trị trước / sau, số quyết định, người duyệt |
| **Hồ sơ bảo hiểm** | lưới | Hệ thống tự đề xuất danh sách cần báo tăng / giảm / đổi lương trong tháng, HR tick chọn rồi xuất một lô |
| **Thôi việc** | 3 bước | Chọn lý do + ngày làm việc cuối → hệ thống tính trợ cấp và phép năm còn lại → chốt, khóa tài khoản |

### Module CHẤM CÔNG — 7 màn

| Tab | Kiểu | Nội dung |
|-----|------|----------|
| **Bảng công ngày** | lưới | Cột: Tổ, Ca, Vào, Ra, Công, TC, Lễ, Mã nghỉ, Ghi chú. Dòng lỗi tô nền. Chip "Chỉ hiện cần xử lý". Sửa tại chỗ `F2`, dán khối Excel |
| **Tổng hợp tháng** | lưới | Một dòng một người. Nhóm cột: Giờ thường, Tăng ca (3), Nghỉ theo mã (14). Mặc định chỉ hiện cột tổng mỗi nhóm |
| **Duyệt nghỉ phép** | lưới | **Hàng đợi duyệt, có ô chọn nhiều dòng.** Cột: MSNV, Họ tên, Tổ, Loại nghỉ, Từ–đến, Số ngày, Số dư phép còn lại. Chọn nhiều rồi Duyệt / Từ chối một lần |
| **Sổ phép năm** | chia đôi | Trái: số dư toàn công ty (đầu kỳ, tích lũy, đã dùng, còn lại). Phải: sổ bút toán của người đang chọn |
| **Ca làm việc** | chia đôi | Trái: danh mục ca. Phải: lịch tháng dạng bảng, hàng là tổ, cột là ngày. Kéo chọn nhiều ô để gán hàng loạt |
| **Đồng bộ Mitapro** | lưới | `sync_jobs`: thời điểm, trạng thái, đọc/chèn/bỏ qua, lỗi. Nút chạy lại một khoảng ngày. Cảnh báo khi quá N giờ không có dữ liệu mới. Kèm mục "punch chưa khớp người" |
| **Báo cáo** | lưới | Đi trễ về sớm theo tổ, tỷ lệ tăng ca theo bộ phận, vắng mặt theo tuần |

### Module TÍNH LƯƠNG — 7 màn

| Tab | Kiểu | Nội dung |
|-----|------|----------|
| **Kỳ lương** | bảng thẻ | Mở → Đang tính → Đã tính → Đã phát hành → Đã chốt. Mỗi thẻ hiện số người, tổng quỹ, số phiếu chưa xác nhận |
| **Bảng lương** | lưới | Ghim MSNV + Họ tên trái, Thực lãnh phải. **5 chế độ xem đặt sẵn**: Gọn · Công · Phụ cấp · Khấu trừ · Đầy đủ. Cột chênh lệch so với kỳ trước, tô màu khi lệch quá ngưỡng |
| **Phiếu lương** | chia đôi | 3 khối ngang: Ngày công & nghỉ · Trợ cấp · Khấu trừ. Thanh dưới neo Tổng thu nhập, Thu nhập chịu thuế, Thực lãnh, số dư phép |
| **Chạy thử** | chia đôi | Chọn gói chính sách, kỳ, phạm vi. Kết quả hiện cạnh số hiện tại để so sánh, **không ghi vào CSDL** |
| **Điều chỉnh** | lưới | Tạm ứng, truy lĩnh, khấu trừ khác. Nhập nhanh nhiều dòng, mỗi dòng gắn mã khoản, lý do bắt buộc |
| **Thưởng** | lưới | Theo năm và đợt. Nhập hệ số hoặc số tiền, xem trước tổng quỹ, đẩy sang kỳ lương đã chọn |
| **Khiếu nại** | chia đôi | Trái: danh sách theo trạng thái. Phải: đối chiếu số công nhân thấy với số hệ thống tính, kèm lần quẹt thẻ gốc |

### Module QUẢN TRỊ — 6 màn

| Tab | Nội dung |
|-----|----------|
| **Gói chính sách** | Trái: danh sách phiên bản. Phải: 6 tab con — Bảo hiểm & thuế · Chuyên cần · Phép năm · Tăng ca · Phụ cấp · Lịch làm việc. Nút Xem ảnh hưởng, duyệt 3 bước |
| **Danh mục** | Loại nghỉ (14) · Khoản lương · Chức vụ (52) · Công việc (82) · Lý do thôi việc (5) · Loại HĐ (4) · Quan hệ thân nhân (6) · Lookup hồ sơ |
| **Tổ chức** | Cây 2 cấp kéo thả. Phải: thuộc tính tổ, ca mặc định, khoảng hiệu lực, số nhân viên đang thuộc |
| **Máy & tích hợp** | Chuỗi kết nối SQL Server Mitapro, chu kỳ sync, độ chồng lấn, số ngày lấy lùi, 3 máy Ronald Jack, URL mã QR công nhân |
| **Phân quyền** | Ma trận **vai trò × tab**, mỗi ô là Xem / Sửa / Duyệt / Không. Chính sách mật khẩu, số lần sai trước khi khóa |
| **Nhật ký** | Gộp `audit_logs`, `policy_confirm_logs`, `sync_jobs`, lần mở lại kỳ, lần reset mật khẩu |

### Cổng CÔNG NHÂN — 3 màn (giữ gần nguyên, thêm xin nghỉ)

| Tab | Nội dung |
|-----|----------|
| **Phiếu lương** | Một trang cuộn dọc, chữ to. Thực lãnh nổi bật trên cùng, chi tiết bung theo nhóm. Nút Xác nhận và Khiếu nại |
| **Bảng công** | Lịch tháng, ô ngày hiện giờ vào ra và mã nghỉ. Chạm vào ngày để xem lần quẹt thẻ |
| **Phép năm** | Ba số lớn: được cấp, đã dùng, còn lại. Bên dưới là lịch sử. **Thêm nút xin nghỉ** |

---

## 23.5 THAO TÁC HÀNG LOẠT — BẮT BUỘC

Đây là chỗ quyết định phần mềm mới nhanh hơn hay chậm hơn GenusSuite. HR không làm việc với một
người, họ làm với cả tổ. **Mọi lưới đều có cột chọn ở đầu và một thanh hành động chỉ hiện ra khi
có dòng được chọn.**

| Màn hình | Thao tác | Ràng buộc an toàn |
|----------|----------|-------------------|
| Duyệt nghỉ phép | Chọn nhiều đơn → Duyệt / Từ chối một lần, một lý do chung | Đơn vượt số dư phép **bị loại khỏi lô và báo rõ**, không im lặng bỏ qua |
| Bảng công ngày | Gán cùng mã nghỉ, đặt cùng giờ vào/ra, xóa ghi chú | Không cho sửa ngày thuộc kỳ đã chốt |
| Danh sách NV | Chuyển tổ, đổi ca mặc định, mở khóa + reset mật khẩu | Chuyển tổ phải nhập ngày hiệu lực, ghi vào `employee_assignments` |
| Bảng lương | Tính lại chọn lọc, phát hành phiếu | Chỉ trên kỳ đang mở; hiện số dòng sẽ đổi trước khi chạy |
| Hồ sơ bảo hiểm | Tick danh sách đề xuất → xuất một lô | Lô đã nộp thì khóa, sửa phải tạo lô điều chỉnh |
| Thưởng | Áp một hệ số cho cả tổ hoặc cả bộ phận | Xem trước tổng quỹ trước khi ghi |

### Ba luật cho mọi thao tác hàng loạt
1. **Luôn xem trước**: "sẽ đổi 47 dòng, 3 dòng bị bỏ qua vì …"
2. **Một giao dịch**: hỏng một dòng thì không ghi dòng nào
3. **Một dòng audit cho cả lô**, kèm danh sách mã nhân viên

---

## 23.6 NHẬP LIỆU NHANH

| Cơ chế | Chi tiết |
|--------|----------|
| **Tạo NV rút gọn** | Form tạo mới chỉ hỏi **9 trường bắt buộc trên MỘT màn**, không bắt đi qua 6 tab. Sáu tab chỉ dùng khi sửa hồ sơ đã có |
| Dán từ Excel | `Ctrl+V` một khối vào lưới chấm công, điều chỉnh lương, thưởng |
| Nhập Excel có đối chiếu | Tải lên → xem bảng so sánh dòng nào thêm / sửa / lỗi → mới xác nhận ghi |
| Xuất Excel | Xuất **đúng cột đang hiện và đúng bộ lọc đang bật**, không xuất toàn bộ bảng |
| Mẫu tải sẵn | Mỗi màn nhập có nút tải file mẫu đúng định dạng |

---

## 23.7 CẢNH BÁO LỖI

| Lúc nào | Cách báo |
|---------|----------|
| Đang gõ | Sai định dạng thì viền ô đổi màu ngay, không đợi bấm Lưu |
| Rời ô | Kiểm tra nghiệp vụ: ngày kết thúc trước ngày bắt đầu, lương dưới mức tối thiểu vùng |
| Trước khi lưu | Gom mọi lỗi lên một danh sách, bấm vào lỗi thì **nhảy tới đúng ô** |
| Lỗi cả lô | Bảng riêng liệt kê dòng lỗi kèm **số dòng gốc trong file Excel** |
| Cảnh báo mềm | Không chặn nhưng hỏi lại: lương tăng trên 50%, nghỉ trên 10 ngày liên tục |

---

## 23.8 GIẢM SỐ LẦN BẤM CHUỘT

| Vấn đề | Cách xử lý |
|--------|-----------|
| Vào việc hằng ngày mất 3–4 lần bấm | **Trang chủ theo vai trò** có thẻ việc cần làm: "29 ca lỗi hôm nay · 12 đơn phép chờ duyệt · 4 HĐ sắp hết hạn" — bấm thẳng vào màn đã lọc sẵn |
| Mở lại màn hay dùng | Ghim tối đa 5 màn lên thanh trên cùng, nhớ theo từng người dùng |
| Nhớ bộ lọc | Bộ lọc và chế độ xem của mỗi màn được nhớ lần sau, có nút Đặt lại |
| Đi tới nhanh | `Ctrl+K` gõ tên màn hoặc MSNV |
| Duyệt tuần tự nhiều người | Khung chi tiết có nút Trước / Sau để đi hết danh sách mà không quay lại lưới |

---

## 23.9 LƯỚI LỚN: NẠP HẾT HAY PHÂN TRANG

| Lưới | Quy mô thật | Cách làm |
|------|-------------|----------|
| Danh sách nhân viên | 438 dòng | Nạp hết một lần, lọc và sắp xếp phía trình duyệt |
| Bảng công ngày | 353 dòng / ngày | Nạp hết một lần |
| Bảng lương một kỳ | 347 dòng × 40 cột | Nạp hết, dùng cuộn ảo của AG-Grid |
| **Dữ liệu quẹt thẻ gốc** | ~320 nghìn dòng / năm | **Bắt buộc phân trang phía máy chủ**, luôn kèm khoảng ngày |
| **Nhật ký thao tác** | tăng không giới hạn | **Phân trang phía máy chủ**, mặc định 30 ngày gần nhất |

---

## 23.10 Thư viện CSS

`apps/web` hiện dùng **CSS thuần** trong `global.css`, chưa có Tailwind. AG-Grid v33 đã có sẵn và
đang chạy. Pattern fixed-viewport (`height:100vh; overflow:hidden`) đã tồn tại ở `.hr-shell`.

Lập trình viên **tự chọn** thêm Tailwind hay mở rộng CSS hiện có. Mọi kích thước trong file này
đều ghi bằng pixel nên không ảnh hưởng thiết kế. **Không đổi AG-Grid sang thư viện khác.**

---

## 23.11 Backlog UI — phiên 2026-08-12 (audit, chưa code)

> Chi tiết đầy đủ: **`BAO_CAO_UI_UX_20260812_PM.md`** · Bàn giao: **`BAN_GIAO_PHIEN_20260812.md`**

| ID | Mức | Việc | §23 |
|----|-----|------|-----|
| U1 | P0 | FAB Trợ Lý AI không che lưới | — |
| U2 | P0 | Dropdown phụ cấp hồ sơ — không lẫn khoản lương | 23.3 |
| U3 | P0 | Mở hồ sơ: double-click dòng hoặc nút Xem | — |
| U4 | P1 | Toolbar HR/Lương/Chấm công ≤46px, không wrap (1366) | 23.1 |
| U5 | P1 | Cột tiền canh phải; Loại HĐ/Tài khoản không cắt chữ | 23.2 |
| U6 | P2 | Chấm công: giảm split-panel / gom tab phụ | — |
| U7 | P2 | Tooltip nút disabled; status bar đếm NV | 23.1 |

**Đã đạt (giữ):** FullScreenSheet hồ sơ · Lưu không nhảy trang · grid cuộn trong vùng dữ liệu · kỳ mặc định tháng hiện tại.

---

*Tiếp: `24_LO_TRINH_5_DOT.md`*
