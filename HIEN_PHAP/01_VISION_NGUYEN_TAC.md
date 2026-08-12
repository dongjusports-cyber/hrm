# 01 — Tầm nhìn, Vai trò, Nguyên tắc vàng

## 1.1 Bối cảnh

| Hạng mục | Giá trị |
|----------|---------|
| Công ty | DONGJU Sports Việt Nam (1 nhà máy) |
| Quy mô | ~500 nhân sự (công nhân + văn phòng) |
| Người chủ phần mềm | Nguyễn Thanh Thiện — Admin hệ thống, **không có IT nội bộ** |
| Mô hình vận hành | Chủ chỉ đạo nghiệp vụ → AI viết code / sửa lỗi / triển khai |
| Giai đoạn 1 | Chạy local **Windows 10 Pro, i3, RAM 16GB** để test |
| Giai đoạn 2 | Đưa lên **Cloud VPS Việt Nam** (rẻ, ổn định, nhanh) |
| Ngôn ngữ UI | **100% Tiếng Việt** |
| Người dùng Web | Admin, HR, Kế toán lương (và user được phân quyền) |
| Người dùng Mobile | Công nhân — portal riêng, xem phiếu lương |

## 1.2 Vai trò & trách nhiệm

| Vai trò | Việc được làm | Việc không làm |
|---------|---------------|----------------|
| **Admin (Chủ)** | Phân quyền, cấu hình policy, mở kỳ lương, quyết định cuối khiếu nại | Không cần sửa code |
| **AI / Developer** | Thiết kế, code, fix bug, viết migration, hướng dẫn deploy | Không tự đổi policy nghiệp vụ |
| **HR** | Nhân sự, chấm công, hỗ trợ khiếu nại | Không vào Cấu Hình (trừ khi được cấp) |
| **Kế toán lương** | Tính lương, BH, xử lý khiếu nại lương | Không sửa công thức gốc nếu không có quyền |
| **Công nhân** | Xem phiếu, xác nhận hoặc khiếu nại | Không AI, không sửa dữ liệu |

## 1.3 Nguyên tắc vàng (bắt buộc)

### P1 — Zero Hard-code Policy
Mọi con số nghiệp vụ (tiền chuyên cần, %, hệ số OT, mẫu số, trần BHXH, bậc phạt trễ…) **không** nằm trong source code. Chúng nằm trong **Policy Engine / Tab Cấu Hình**, có `effective_from` / `effective_to`, có **version**, và mỗi phiếu lương **snapshot** policy đã dùng.

### P2 — Metadata-driven Architecture
- Công thức lương = biểu thức + tham số cấu hình
- Portal tabs = metadata (thêm/xóa/đổi tên/thứ tự qua Tab 8)
- Form, báo cáo, loại nghỉ, loại phụ cấp = catalog cấu hình được

### P3 — Modular theo khoa học lợi ích (chia nhỏ để trị — có điều kiện)
Mỗi **domain nghiệp vụ** = 1 module độc lập (import rõ ràng). Mục tiêu: **hư cái nào sửa cái đó**, không lan sang module khác.

**Không** tách file chỉ vì “file lớn”. Chỉ tách khi mang lại lợi ích rõ (xem **P3b** và file `06` mục 6.6a).

### P3b — Luật tách / không tách file (bắt buộc)
Chủ phần mềm không phải IT — AI phải tự áp dụng luật sau khi tổ chức code:

| Được tách (nên tách) | Không được tách (giữ nguyên dù file lớn) |
|----------------------|------------------------------------------|
| Hai domain khác nhau (payroll ≠ attendance) | Một **công thức / state machine** đang đọc tuần tự — tách ra dễ lệch thứ tự |
| Ranh giới API rõ (router / service / model) | File UI một màn hình gắn chặt (cùng state, cùng form) — tách làm rối |
| Policy catalog vs Formula engine | Snapshot + calculate cùng lifecycle — giữ gần nhau nếu tách làm mất ngữ cảnh |
| Worker Portal vs HR Portal | Copy-paste “cho nhỏ file” tạo 2 nơi sửa 1 bug |
| Test / migration / agent riêng | Tách theo số dòng (~500, ~1000) **không** có lý do nghiệp vụ |

**Kiểm tra trước khi tách:**  
1) Sửa bug A có bắt buộc mở file B không? → Nếu có và hai thứ cùng một ý niệm → **đừng tách**.  
2) Hai phần có thể deploy/test/hiểu độc lập không? → Nếu có → **tách**.  
3) Tách xong có dễ hiểu hơn với người không IT + AI phiên sau không? → Nếu không → **giữ**.

### P4 — Decimal cho tiền
Mọi tiền tệ: `Decimal` (Python) / string hoặc decimal-safe trên FE. **Cấm** `float` cho tiền.

### P5 — Portal 8 ô, không Sidebar
Màn hình chính = lưới icon (kiểu điện thoại). Không slidebar. Bên trong module có thể có tab ngang / breadcrumb Lv2–Lv4.

### P6 — Phân quyền minh bạch
8 ô **luôn hiện đủ**. Không ẩn, không làm mờ. Click ô không có quyền → thông báo tiếng Việt.

### P7 — AI read-only với dữ liệu nghiệp vụ
AI **không** tự sửa lương, không đổi policy, không khóa kỳ. Chỉ nhắc việc, giải thích, rà soát, đề xuất.

### P8 — Xác nhận phiếu = khóa
Công nhân xác nhận phiếu lương → **không** khiếu nại / sửa đổi phiếu đó (trừ Admin mở lại bằng quy trình đặc biệt có log).

### P9 — Lỗi tiếng Việt
Mọi lỗi API/UI: tiếng Việt, gọi tên user khi có. Ví dụ:  
`COSMOS AI xin chào Nguyễn Văn A, bạn không có quyền truy cập. Vui lòng liên hệ Admin.`

### P10 — Xác nhận 3 lần khi sửa số tiền (Admin)
Khi Admin sửa tham số liên quan tiền trong Cấu Hình → bắt buộc **xác nhận 3 bước** trước khi Save (modal 1 → 2 → 3).

### P11 — Vừa đủ, không phức tạp (KISS / YAGNI) — luật tối cao về quy mô
> Hiến pháp vững thì phần mềm chắc, nhưng **không rườm rà, nặng nề, chậm, phức tạp**.

Bối cảnh: **1 nhà máy, ~500 người, không IT, chạy local trước rồi VPS VN.** Mọi quyết định kỹ thuật phải cân xứng quy mô này.

**Bắt buộc:**
- Chọn giải pháp **đơn giản nhất mà vẫn đúng & an toàn**. Không thêm tính năng “phòng xa” chưa ai cần (YAGNI).
- Trước khi thêm 1 lớp/công cụ/thư viện mới, AI phải trả lời được: *“500 người, 1 nhà máy có thật sự cần cái này không?”* Nếu không → bỏ.
- Ưu tiên **Modular Monolith 1 tiến trình** + PostgreSQL + Redis. **Cấm** đề xuất microservices, Kubernetes, message broker nặng (Kafka…), event-sourcing, multi-region khi chưa có nhu cầu thực.
- Tài liệu/chương trong Hiến pháp giữ **ngắn, thực dụng**. Đủ để làm đúng, không viết cho “đẹp lý thuyết”.
- Nếu một yêu cầu bảo mật/vận hành làm hệ thống chậm hoặc khó dùng mà lợi ích nhỏ → nêu đánh đổi cho Chủ quyết, không tự ý làm nặng.

**Thang đo “vừa đủ”:** trang thường tải < 2s; tính lương 500 người < 2 phút; người không IT thao tác được không cần cầm tay.

## 1.4 Phạm vi MVP vs Sau

| Phạm vi | MVP | Phase 2+ |
|---------|-----|----------|
| Nhân sự cơ bản | ✅ | |
| Sync Mitapro + công | ✅ | |
| Tính lương + BHXH/BHYT/BHTN + CD | ✅ | |
| Phiếu lương Worker (xác nhận/khiếu nại) | ✅ | |
| AI nhắc việc (rule) | ✅ | |
| AI hỏi đáp Gemini (user có quyền) | ✅ | |
| TNCN / thuế | ❌ | ✅ Kế toán đang dùng phần mềm riêng |
| App Store native | ❌ | PWA đủ |
| Multi-nhà máy | ❌ | Sẵn `tenant_id` nếu cần |

## 1.5 Công nghệ tư duy đệ quy (bắt buộc khi phát triển)

Mọi phiên AI phải áp dụng:

1. **Snapshotting** — Chụp trạng thái: file đã đụng, schema, quyết định liên quan
2. **Contextual Anchoring** — Neo vào Hiến pháp + kỳ lương mẫu (Oct/2025 Excel)
3. **Modular Code Mapping** — Mỗi thay đổi map vào module cụ thể (file 08)
4. **Hợp đồng báo cáo chuyển giao** — Kết thúc phiên theo mẫu file 08

## 1.6 Nguồn dữ liệu chuẩn để đối chiếu

| Nguồn | Dùng để |
|-------|---------|
| `2.Salary table for Sep/Oct/Nov/Dec.2025.xlsx` | Regression tính lương |
| `Attendance - Overtime - Turnover Report 2026.xlsx` | KPI chấm công / OT / turnover |
| `Cách tính lương.docx` | Seed policy mặc định (chuyên cần, OT, PC) |
| `Máy chấm công.txt` | Mitapro + `.\SQLEXPRESS` / `MITACOSQL` |
| `SQL_mitapro.BAK` | Schema Mitapro (khi implement Agent) |

*Tiếp: `02_UI_PORTAL_PHAN_QUYEN.md`*
