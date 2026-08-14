# 20 — HIẾN PHÁP V2: QUY TRÌNH LÀM VIỆC

> **Đọc file này TRƯỚC MỌI PHIÊN CODE.**
> Phiên bản **2.0** · Ngày **2026-08-10** · Chủ sở hữu: **Nguyễn Thanh Thiện**
> Trạng thái: **ĐỦ ĐIỀU KIỆN VIẾT CODE**

---

## 20.0 Bộ V2 này là gì

Bộ 00–15 là hiến pháp dựng phần mềm từ số không, đã hoàn thành vai trò: DJ HRM hiện chạy được
với 26 màn hình, 31 bảng, 22 migration.

Bộ 20–24 là hiến pháp **nâng cấp** DJ HRM lên đủ nghiệp vụ thay thế GenusSuite, dựng từ việc
giải mã 70 bảng và 148 thủ tục PL/SQL của phần mềm cũ.

| # | File | Khi nào đọc |
|---|------|-------------|
| 20 | `20_HIEN_PHAP_V2_QUY_TRINH.md` | Mọi phiên — file này |
| 21 | `21_SCHEMA_V2.md` | Phiên đụng cơ sở dữ liệu |
| 22 | `22_QUY_TAC_NGHIEP_VU.md` | Phiên đụng lương hoặc chấm công |
| 23 | `23_UI_MAN_HINH.md` | Phiên đụng giao diện |
| 24 | `24_LO_TRINH_5_DOT.md` | Đầu mỗi đợt, để biết phạm vi và tiêu chí nghiệm thu |
| **25** | **`25_QUY_TAC_THIET_KE_TOI_CAO.md`** | **Mọi phiên UI** — tám chữ vàng thiết kế |
| **26** | `26_TU_DONG_HOA_VAN_HANH.md` | Phiên đụng job nền, Hub HR, auto-duyệt, pipeline tháng |

**Luật ưu tiên khi mâu thuẫn** (cao → thấp):

1. Lời Chủ trong chat (mới nhất thắng)
2. Bộ V2 (20–24)
3. Bộ V1 (00–15)
4. File gốc GenusSuite trong `HIEN_PHAP/GenuSuite HRM/`
5. Mã nguồn hiện tại

Bộ V1 vẫn còn hiệu lực ở những phần V2 không nhắc tới: stack công nghệ, bảo mật, backup,
runbook vận hành, quy ước báo cáo phiên.

---

## 20.1 Điều được giữ lại từ V1 — không bàn lại

- Stack: **FastAPI + SQLAlchemy + PostgreSQL + Alembic**, **React Vite + AG-Grid + TypeScript**,
  Docker Compose, Agent Windows đọc Mitapro.
- Job nền: **Redis + ARQ hoặc RQ** cho tính lương / export / cron (11§) — **không** coi là message
  broker nặng; chi tiết pipeline ở file **26**.
- Mọi tiền tệ dùng **Decimal**, không dùng float.
- Mọi thông báo lỗi UI và API bằng **tiếng Việt**.
- **Không hard-code** thông số nghiệp vụ (tiền, %, hệ số, ngày, ngưỡng).
- **Không** Audit Mode, **không** AI trên Worker Portal.
- Nguyên tắc **Vừa đủ**: giải pháp cân xứng quy mô một nhà máy 500 người, không có đội IT.
  Cấm microservices, cấm Kubernetes, cấm message broker khi chưa cần.

---

## 20.2 Nguyên tắc riêng của V2

### N1. Mở rộng, không đập đi làm lại
DJ HRM đang chạy. Mọi việc là **thêm bảng, thêm cột, thêm màn**. Chỉ sửa cái đang có khi V2 ghi
rõ. Không đổi framework, không đổi thư viện, không đổi cấu trúc thư mục module.

### N2. Dữ liệu test không cần bảo toàn
438 nhân viên và 2.133 phiếu lương hiện có là dữ liệu nạp để thử. **Được phép xóa sạch và nạp
lại** khi cần nắn cấu trúc. Đây là lý do đợt 1 làm nhanh: không phải viết migration khéo léo,
chỉ cần script dựng lại đúng.

### N3. Mọi chính sách có ngày hiệu lực
Không có bảng chính sách nào được phép chỉ lưu "giá trị hiện tại". Sửa chính sách không bao giờ
được làm đổi số của kỳ lương đã chốt.

### N4. Tỷ lệ và ngưỡng là dữ liệu, không phải mã nguồn
Nếu HR có thể muốn đổi nó trong 2 năm tới, nó phải nằm trong bảng hoặc trong
`policy_packages.payload`, và phải sửa được từ màn Admin.

### N5. Dữ liệu thô và dữ liệu đã tính là hai bảng khác nhau
Khi công nhân khiếu nại, hệ thống phải chỉ ra được **lần chấm vân tay gốc** (từ `attendance_punches`). Không bao giờ ghi đè
lên `attendance_punches`.

### N6. Ngày tháng dùng kiểu `date` / `timestamptz` thật
Không lưu ngày dưới dạng chuỗi `YYYYMMDD` như GenusSuite.

### N7. Xóa mềm ở tầng truy cập dữ liệu
Không bắt lập trình viên nhớ thêm điều kiện lọc vào từng câu truy vấn.

### N8. Không nhét thuật toán vào Admin
Admin chứa **số, tỷ lệ, ngày, danh mục**. Công thức tính lương, thứ tự các bước, ràng buộc an
toàn nằm trong mã nguồn. HR đổi nhầm một con số thì sai một khoản; HR đổi nhầm thứ tự bước thì
sai toàn công ty mà không ai phát hiện.

---

## 20.3 Quy trình một phiên làm việc

### Bước 1 — Nhận việc
Một phiên = **một hạng mục** trong file 24. Không gộp nhiều hạng mục. Không nhảy đợt.

### Bước 2 — Đọc trước khi gõ
Bắt buộc: file **20** + file chuyên môn tương ứng (21 / 22 / 23) + phần đợt đang làm trong **24**.
Khi cần tra nghiệp vụ gốc: đọc thẳng `HIEN_PHAP/GenuSuite HRM/*.sql`, **không đoán**.

### Bước 3 — Kiểm tra cái đã có
Trước khi tạo bảng hoặc màn mới, **grep mã nguồn** xem đã tồn tại chưa. Danh sách 31 bảng đang có
nằm ở mục 21.1. Dựng trùng là lỗi nghiêm trọng nhất trong dự án này.

### Bước 4 — Viết code
Thứ tự trong một hạng mục: **model → migration → service → API → test → UI**.
Không viết UI trước khi API chạy được.

### Bước 5 — Tự nghiệm thu
Chạy đúng tiêu chí ghi trong file 24 cho hạng mục đó. Tiêu chí là câu **kiểm chứng được bằng
số**, không phải "đã hoàn thành".

### Bước 6 — Báo cáo
Theo mẫu ở mục 20.6.

---

## 20.4 Điều cấm

| Cấm | Vì sao |
|-----|--------|
| Dựng lại bảng đã có | Xem mục 21.1 trước khi tạo bất kỳ bảng nào |
| Hard-code số tiền, %, ngưỡng, hệ số | Vi phạm N4 |
| Dùng `float` cho tiền | Sai số cộng dồn trên 438 người |
| Sửa số liệu kỳ lương đã chốt | Vi phạm N3 |
| Ghi đè `attendance_punches` | Vi phạm N5 |
| Đổi tên bảng / cột đang có mà không có lệnh | Phá dữ liệu và mã nguồn khác |
| `git commit`, `git push`, deploy | Chỉ khi Chủ yêu cầu |
| Thêm thư viện mới | Phải hỏi trước, trừ khi file 21–23 ghi rõ |
| Tự ý đổi thiết kế trong 21–23 | Thấy sai thì **báo rồi chờ**, không tự sửa |

---

## 20.5 Điều bắt buộc trong mọi đoạn code

```
1. Tiền: Decimal, không float
2. Ngày: date / timestamptz, không chuỗi
3. Thông báo lỗi: tiếng Việt, nói rõ sai ở đâu và sửa thế nào
4. Thao tác hàng loạt: chạy trong một giao dịch, hỏng một dòng thì không ghi dòng nào
5. Mọi thay đổi dữ liệu nghiệp vụ: ghi audit_logs
6. Mọi bảng chính sách: có effective_from, effective_to
7. Truy vấn lưới: có index tương ứng (xem mục 21.6)
8. Không câu truy vấn nào chạy trong vòng lặp (N+1)
```

---

## 20.6 Mẫu báo cáo cuối phiên

```
## Phiên: <mã hạng mục trong file 24>

### Đã làm
- <file đã tạo / sửa, mỗi dòng một ý>

### Nghiệm thu
- Tiêu chí: <chép nguyên câu tiêu chí từ file 24>
- Kết quả: <số thật chạy ra được>

### Lệch so với thiết kế
- <chỗ nào phải làm khác 21/22/23 và vì sao — nếu không có thì ghi "không có">

### Chặn / cần Chủ quyết
- <nếu không có thì ghi "không có">

### Việc tiếp theo
- <mã hạng mục kế tiếp>
```

---

## 20.7 Ba số đã chốt — không được đoán lại

| Khoản | Giá trị | Ghi chú |
|-------|---------|---------|
| Chuyên cần | **600.000** | Mức chuẩn theo tháng 26 ngày công |
| Đi lại | **800.000** | Mức chuẩn theo tháng 26 ngày công |
| Lương thử việc | **85%** | Của lương chính thức |

Phiếu GenusSuite cũ có lúc ghi 623.077 và 830.769 — đó là **tháng 27 ngày công**, đã nhân 27/26.
Công thức đầy đủ ở file 22.

---

## 20.8 Việc còn treo — không chặn đợt 1 và 2

| Việc | Cần trước đợt | Cách lấy |
|------|---------------|----------|
| Cột vào/ra trong bảng `CheckInOut` của Mitapro | Đợt 3 | Chạy `SELECT TOP 5 * FROM CheckInOut` trên SQL Server máy Mitapro |
| Chọn Tailwind hay giữ CSS thuần | Đợt 3 | Lập trình viên tự quyết; kích thước trong file 23 đều ghi bằng pixel nên không ảnh hưởng thiết kế |
| Mẫu in hợp đồng, quyết định, thẻ chấm công | Đợt 5 | Xin mẫu Word hiện hành của phòng HR |
| Pipeline tự động hóa đầy đủ (A2 publish/lock) | **Sau v1.0** | Xem file **26** · code **24§Đợt 6** |

---

## 20.9 Tự động hóa vận hành (tóm tắt)

HR mục tiêu **chỉ xử lý ngoại lệ và cổng duyệt** — phần còn lại chạy nền theo file **26**:

- **L0/L1:** sync, tính công, lương nháp, todo (0 token AI)
- **L2/A3:** chốt công, phát hành lương, xuất BHXH — 1 click
- **H:** policy tiền, khiếu nại, kỷ luật — không auto

Triển khai **sau đóng v1.0**, trừ hạng mục 24§6.x ghi “trong v1.0”.

---

*Tiếp: `21_SCHEMA_V2.md`*
