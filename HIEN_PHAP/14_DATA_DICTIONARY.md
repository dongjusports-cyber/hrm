# 14 — Data Dictionary (từ điển field cốt lõi)

> Chỉ liệt kê field nghiệp vụ hay gây nhầm. Chi tiết bảng xem file `07`.

## 14.1 Nhân viên (`employees`)

| Field | Nghĩa | Ghi chú |
|-------|-------|---------|
| `employee_code` | MSNV | Khóa nghiệp vụ, khớp Mitapro |
| `contract_salary` | Lương hợp đồng | Base lương ngày công (khi chính thức) |
| `probation_salary` | Lương thử việc | Dùng trước ngày ký HĐ |
| `si_contribution_base` | **Lương đóng BH** (base tính OT + base BH) | **TỰ TÍNH** = Lương HĐ + Σ phụ cấp có `include_in_si_base=TRUE` (giá trị đầy đủ). Gồm: chức vụ, độc hại, PCCC, tay nghề, thâm niên. KHÔNG gồm: chuyên cần, đi lại, khác. Đã xác minh 320 NV + NV Bảo hiểm xác nhận |
| `si_base_override` | Ghi đè Lương đóng BH | NULL = dùng giá trị tự tính; chỉ set cho ca ngoại lệ |
| `si_enrolled` | Có tham gia BH kỳ này | CASH/thử việc có thể false |
| `contract_signed_at` | Ngày ký HĐ chính thức | Mốc chuyển thử việc → chính thức |
| `join_date` | Ngày vào làm | Tính thâm niên, phép năm |
| `pay_channel` | ATM / CASH | Kênh chi trả |

## 14.2 Kỳ lương (`pay_periods`)

| Field | Nghĩa |
|-------|-------|
| `official_work_days` | Ngày công chuẩn tháng (đếm từ lịch) |
| `salary_divisor` | Mẫu số chia (rule 27→26, else = official) |
| `status` | open / calculating / published / locked |

## 14.3 Bảng công tháng (`timesheet_months`)

| Field | Nghĩa | Excel |
|-------|-------|-------|
| `worked_days` | Công thực tế (có thể lẻ) | cột O |
| `al_days` | Nghỉ phép năm (có lương) | cột P |
| `rem_days` | Nghỉ chế độ (cty không trả) | cột Q |
| `late_count` | Số lần đi trễ | phạt chuyên cần |
| `early_count` | Số lần về sớm | phạt chuyên cần |
| `ot_hours_weekday/weekend/holiday` | Giờ OT theo loại | base BHXH |

## 14.4 Phiếu lương (`payslips`)

| Field | Nghĩa |
|-------|-------|
| `wd_salary` | Lương ngày công |
| `allowance_total` | Tổng phụ cấp (sau pro-rata & phạt) |
| `ot_pay` | Tiền tăng ca |
| `other_adjustments` | Re-Pay/truy lĩnh/bù trừ (1 danh mục gộp, nhập tay) |
| `gross` | Tổng thu nhập |
| `bhxh/bhyt/bhtn` | Khấu trừ BH (trên mức đóng BHXH) |
| `union_fee` | Công đoàn |
| `other_deductions` | Tạm ứng, phạt… |
| `pit_amount` | TNCN — **=0 ở MVP** (Phase 2) |
| `net` | Thực lãnh |
| `policy_snapshot_id` | Policy đóng băng khi tính |
| `status` | draft…confirmed…locked |

## 14.5 Từ viết tắt

| Viết tắt | Nghĩa |
|----------|-------|
| HĐ | Hợp đồng |
| PC | Phụ cấp |
| OT | Tăng ca (Overtime) |
| BHXH/BHYT/BHTN | BH Xã hội / Y tế / Thất nghiệp |
| CD | Công đoàn |
| AL | Annual Leave — phép năm |
| REM | Nghỉ chế độ nhà nước |
| MSNV | Mã số nhân viên |

*Tiếp: `15_RUNBOOK_KHONG_IT.md`*
