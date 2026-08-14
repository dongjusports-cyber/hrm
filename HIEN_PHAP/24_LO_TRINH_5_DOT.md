# 24 — LỘ TRÌNH 5 ĐỢT

> Một phiên Cursor = **một mã hạng mục**. Không gộp. Không nhảy đợt.
> Tiêu chí nghiệm thu là câu **kiểm chứng được bằng số** — không phải "đã hoàn thành".

---

## 24.0 Luật vàng của lộ trình

**Thứ tự này bắt buộc, không được đảo:**

```
Cây tổ chức  →  Danh mục & chính sách  →  Chấm công  →  Lương  →  Admin đầy đủ
```

Hồ sơ móc vào tổ. Chấm công cần ca làm việc và loại nghỉ. Lương cần bảng công.
Làm ngược thứ tự thì **mỗi bước đều phải sửa lại bước trước**.

**Dữ liệu test được phép xóa.** 438 nhân viên và 2.133 phiếu lương hiện có là dữ liệu nạp để
thử. Không cần viết migration khéo léo để giữ chúng — cứ xóa sạch và nạp lại bằng script.

---

# ĐỢT 1 — CÂY TỔ CHỨC

**Mục tiêu:** DJ HRM có hai cấp Bộ phận › Tổ, mọi nhân viên thuộc về một tổ.

| Mã | Hạng mục | Nội dung |
|----|----------|----------|
| **1.1** | Model + migration tổ chức | Bảng `teams`, `positions`, `jobs`; mở rộng `departments` (4 cột + ngày hiệu lực); thêm `employees.team_id`, `position_code`, `job_code` |
| **1.2** | Script dựng lại dữ liệu | Xóa sạch nhân viên + phiếu lương test. Nạp 10 bộ phận từ `TCO_EODEPT`, 73 tổ từ `THR_ABWORKGRP`, 52 chức vụ, 82 công việc |
| **1.3** | Nạp lại lương GenusSuite | Chạy lại `import_genussuite_2026.py` với ánh xạ tổ đúng. Line 1–12 đóng `effective_to = 2026-06-30`, 5 tổ mới mở `effective_from = 2026-07-01` |
| **1.4** | API + lưới danh sách NV | Bộ lọc Bộ phận › Tổ, ghim cột, chế độ xem Gọn, xuất Excel theo bộ lọc |
| **1.5** | `employee_assignments` | Bảng lịch sử đổi tổ + chuyển tổ hàng loạt từ lưới |

### Nghiệm thu đợt 1
- [ ] Lưới nhân sự hiện đúng **Bộ phận › Tổ** cho cả 438 người
- [ ] Lọc theo bộ phận `Sewing` ra đúng số người, lọc theo tổ `Sewing CB 1` ra tập con
- [ ] Truy vấn "tổ của MSNV 1514 vào ngày 2026-03-15" trả về tổ **của tháng 3**, không phải tổ hiện tại
- [ ] Bảng `departments` còn đúng **10 dòng**; `teams` có **73 dòng**
- [ ] Không còn cột `employees.department_id`

---

# ĐỢT 2 — DANH MỤC VÀ CHÍNH SÁCH

**Mục tiêu:** mọi con số nghiệp vụ nằm trong bảng hoặc payload, HR sửa được từ Admin.

| Mã | Hạng mục | Nội dung |
|----|----------|----------|
| **2.1** | `lookup_values` | Danh mục phẳng: dân tộc, tôn giáo, quốc tịch, nơi sinh, nơi cấp CCCD, trình độ |
| **2.2** | `leave_types` mở rộng | Đủ **14 mã** với `pay_ratio_percent` theo bảng 22.6. `PER` để `NULL`, buộc HR khai |
| **2.3** | `pay_components` | Đổi tên từ `allowance_types`, thêm 5 cột cờ, nạp ~30 mã |
| **2.4** | `work_shifts` + `team_shift_schedules` | Một ca hành chính 08:00–17:00, gán mặc định cho tổ |
| **2.5** | Bảng chính sách có ngày hiệu lực | `insurance_rates`, `pit_brackets`, `pit_deductions`, `seniority_allowance_tiers`, `attendance_bonus_rules` |
| **2.6** | Mở rộng `policy_packages.payload` | Theo đúng khối JSON ở mục 22.12; sửa 3 lỗi validator ở mục 22.3 |
| **2.7** | `roles` + `role_permissions` | Ma trận vai trò × tab; quyền hiệu lực = vai trò rồi mới đến `user_permissions` |
| **2.8** | Màn Admin › Danh mục + Gói chính sách | Đọc/ghi bản nháp, duyệt 3 bước (nền `policy_confirm_logs` đã có) |

### Nghiệm thu đợt 2
- [ ] Đổi **ngưỡng chuyên cần** từ 3/2 sang 4/3 trên màn Admin → chạy thử ra kết quả khác, **không sửa một dòng code nào**
- [ ] Đổi **tiền chuyên cần** 600.000 → 650.000 chỉ áp cho kỳ mới, kỳ đã chốt giữ nguyên số
- [ ] Thêm một loại nghỉ mới từ màn Danh mục, nó hiện ngay trong ô chọn ở màn chấm công
- [ ] Tạo vai trò "Kế toán lương" chỉ xem được module Tính Lương, đăng nhập thử đúng như vậy
- [ ] Bậc thâm niên 136 tháng tra ra **550.000**

---

# ĐỢT 3 — CHẤM CÔNG

**Mục tiêu:** bảng công ngày dùng được hằng ngày, đơn nghỉ phép duyệt được hàng loạt.

| Mã | Hạng mục | Nội dung |
|----|----------|----------|
| **3.1** | `attendance_punches` mở rộng | Thêm `employee_id`, `direction`, `sync_job_id`; map MSNV/MaChamCong (vân tay Mitapro) lúc nạp |
| **3.2** | Lọc chấm liên tục | Gom trong cửa sổ 60 giây (vân tay hay bấm nhiều lần), giữ sớm nhất = vào, muộn nhất = ra |
| **3.3** | Tính công một ngày | Ca 08:00–17:00, trừ 1 giờ trưa, trễ/sớm dung sai 0 giây, phần sau 17:00 là tăng ca |
| **3.4** | `attendance_days` mở rộng | Thêm 10 cột theo mục 21.5, gồm `segment` |
| **3.5** | `timesheet_month_details` | Tổng hợp theo `category` × `segment` |
| **3.6** | `leave_requests` + màn Duyệt nghỉ phép | Hàng đợi có ô chọn nhiều dòng, duyệt/từ chối hàng loạt trong một giao dịch |
| **3.7** | Màn Bảng công ngày | Sửa tại chỗ `F2`, dán khối Excel, chip "Chỉ hiện cần xử lý", thao tác hàng loạt |
| **3.8** | Màn Đồng bộ Mitapro | Hiện `sync_jobs`, chạy lại một khoảng ngày, danh sách punch chưa khớp người |

### Nghiệm thu đợt 3
- [ ] Dán một khối Excel 20 dòng vào lưới chấm công và **lưu được**
- [ ] Chip "Chỉ hiện cần xử lý" lọc ra đúng các ca thiếu giờ vào hoặc giờ ra
- [ ] Duyệt **12 đơn phép bằng một lần bấm**; đơn vượt số dư bị loại khỏi lô và báo rõ lý do
- [ ] Một người chấm vân tay 5 lần liên tiếp lúc 07:50 → hệ thống ghi **một** giờ vào
- [ ] Người vào lúc 07:59:59 → không đi trễ. Vào lúc 08:00:01 → **đi trễ**
- [ ] Người ra lúc 20:00 → công = 1,0 và tăng ca = 3,0 giờ

---

# ĐỢT 4 — TÍNH LƯƠNG

**Mục tiêu:** engine mới tính ra đúng từng đồng so với phiếu GenusSuite.

| Mã | Hạng mục | Nội dung |
|----|----------|----------|
| **4.1** | `payslip_components` | Có `segment` và `seq_no`; mỗi khoản là một dòng |
| **4.2** | Lương ngày công + lương ngày nghỉ | Theo mục 22.4 và 22.6, tách `probation` / `official` |
| **4.3** | Chia phụ cấp | `divisor = min(ngày lịch, 26)`, tử số theo mục 22.3 |
| **4.4** | Tỷ lệ chuyên cần | Theo `F_CAL_INDUS_AMT`, đủ cả ba điều kiện miễn trừ |
| **4.5** | Tăng ca | Nền OT khác nền BHXH; hệ số 1,5 / 2,0 / lễ quá 8 giờ |
| **4.6** | Bảo hiểm + thuế | Nền BHXH theo mục 22.9, trần 46.800.000; tách `taxable_income` khỏi `net` |
| **4.7** | Sổ phép năm | `annual_leave_ledger` + `annual_leave_entries` dạng bút toán |
| **4.8** | `employee_bonuses` | Thưởng Tết nhiều đợt, đẩy vào kỳ lương |
| **4.9** | Màn Bảng lương + Phiếu lương | 5 chế độ xem, 3 khối, thanh tổng neo dưới |
| **4.10** | Màn Chạy thử | Mô phỏng cạnh số hiện tại, **không ghi CSDL** |

### Nghiệm thu đợt 4
- [ ] **Bài kiểm chứng MSNV 1519 kỳ 07/2026 (mục 22.11) khớp từng đồng.** Thực lãnh phải ra đúng **9.682.398**
- [ ] Người thử việc: chuyên cần và đi lại = **0**
- [ ] Người vào giữa tháng: phiếu có **hai dòng** lương ngày công, `probation` và `official`
- [ ] Tháng 27 ngày công, đi đủ: chuyên cần = **623.077**
- [ ] Tháng giả lập 20 ngày công, đi đủ: chuyên cần = **600.000**
- [ ] Số dư phép in trên phiếu = tổng các dòng bút toán trong sổ
- [ ] Chốt kỳ xong, sửa gói chính sách → số của kỳ đã chốt **không đổi**

---

# ĐỢT 5 — HOÀN THIỆN

| Mã | Hạng mục | Nội dung |
|----|----------|----------|
| **5.1** | Hồ sơ nhân viên đầy đủ | 18 cột mới, 6 tab, form tạo mới rút gọn 9 trường |
| **5.2** | `labour_contracts` | Lịch sử HĐ, cảnh báo hết hạn 60 ngày |
| **5.3** | `employee_family_members` | Giảm trừ gia cảnh tính ra từ bảng, không nhập tay |
| **5.4** | `employee_resignations` | 5 lý do, tính trợ cấp và phép tồn, cho phép nghỉ nhiều lần |
| **5.5** | `insurance_declarations` | Tự đề xuất danh sách báo tăng/giảm tháng, xuất theo lô |
| **5.6** | Admin đủ 6 tab | Tổ chức, Máy & tích hợp, Phân quyền, Nhật ký hợp nhất |
| **5.7** | Trang chủ theo vai trò | Thẻ việc cần làm, ghim màn, `Ctrl+K` |
| **5.8** | Cổng công nhân | Thêm màn xin nghỉ phép |
| **5.9** | Mẫu in | Hợp đồng, quyết định (không còn thẻ quẹt — dùng vân tay Mitapro) |

### Nghiệm thu đợt 5
- [ ] Tạo một nhân viên mới chỉ bằng **9 trường trên một màn**
- [ ] HĐ hết hạn trong 60 ngày hiện trên trang chủ và trong tab Hợp đồng
- [ ] Người có 2 con dưới 18 tuổi → giảm trừ tự ra **11.000.000 + 2 × 4.400.000**
- [ ] Một nhân viên nghỉ việc rồi vào lại, hệ thống ghi được **2 dòng** thôi việc
- [ ] Xuất được một lô báo tăng BHXH của tháng
- [ ] HR trưởng đổi chính sách sang kỳ mới **không cần lập trình viên**

---

## 24.6 Cách giao việc

**Đừng giao cả 5 đợt một lần.** Giao **đợt 1** trước và nghiệm thu bằng đúng 5 gạch đầu dòng ở
trên. Đợt 1 nắn lại cấu trúc mà mọi thứ khác móc vào — sai ở đây thì bốn đợt sau đều phải làm
lại. Bốn đợt sau có thể chạy liền mạch hơn.

Trong một đợt, giao lần lượt từng mã hạng mục. Mỗi mã xong thì báo cáo theo mẫu ở file 20 mục 20.6.

## 24.7 Phần mềm không có ngày nào chết

Mỗi đợt xong là dùng được ngay. HR chạy song song DJ HRM và GenusSuite, đối chiếu số cho tới khi
tin tưởng rồi mới cắt hẳn phần mềm cũ. Không có mốc "tắt GenusSuite" trong lộ trình này — đó là
quyết định của Chủ khi thấy số đã khớp đủ lâu.

---

# ĐỢT 6 — TỰ ĐỘNG HÓA VẬN HÀNH

> **Sau v1.0** (trừ **6.1** có thể làm sớm khi bật job lương ở Đợt 4). Chi tiết: **`26_TU_DONG_HOA_VAN_HANH.md`**.

**Mục tiêu:** HR mở **Operations Hub** — sửa ngoại lệ + bấm cổng; máy lo sync → công → lương nháp.

| Mã | Hạng mục | Nội dung |
|----|----------|----------|
| **6.1** | Worker ARQ/RQ | Job `calculate_period`, export lớn; API trả `job_id` + progress (**trong v1.0** nếu Đợt 4 cần) |
| **6.2** | `ops_exceptions` + detector | Rule phát hiện ca lỗi, Δ lương, punch mồ côi → ghi exception |
| **6.3** | Operations Hub UI | Gom todo + exception + alert; link màn đã lọc (23§23.8, 24§5.7) |
| **6.4** | Cron hằng ngày | Sync + tính công ngày (02:00 seed); rollup cuối tháng |
| **6.5** | `leave_auto_rules` + auto-duyệt | Đơn phép trong ngưỡng → approved + gán mã lên bảng công |
| **6.6** | Pipeline tháng | Ngày 1: accrual phép + lương nháp; todo Δ; không bắt HR bấm Tính lương |
| **6.7** | Cổng A2 (tuỳ chọn) | Auto chốt công / auto publish khi 0 exception — **chỉ sau 2 kỳ khớp GenusSuite** |

### Nghiệm thu đợt 6

- [ ] Tiêu chí **26§26.7** (7 mục) — copy nguyên câu khi báo cáo phiên
- [ ] HR pilot 1 kỳ: thời gian thao tác giảm so với v1.0 (Chủ ghi nhận, không cần số cứng)

**Thứ tự:** 6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6 → 6.7 (6.7 cuối cùng, có thể bỏ qua).

---

*Hết bộ V2 (20–26). Quay lại `20_HIEN_PHAP_V2_QUY_TRINH.md` khi bắt đầu phiên mới.*

---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
