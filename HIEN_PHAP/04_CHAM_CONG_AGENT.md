# 04 — Chấm công, Lịch, Agent Mitapro

## 4.1 Nguồn chấm công

| Hạng mục | Giá trị |
|----------|---------|
| Máy | Ronal Jack (vân tay) |
| Phần mềm máy | **Mitapro** |
| DB | SQL Server `MITACOSQL` trên `.\SQLEXPRESS` |
| Backup tham chiếu | `SQL_mitapro.BAK` |
| Cách lấy dữ liệu | **Agent on-prem** (mô hình giống AMIS) — đọc SQL **read-only**, đẩy lên Cloud/API |

## 4.1b Schema Mitapro (trích từ `SQL_mitapro.BAK` — ĐÃ XÁC MINH)

> Mitapro = phần mềm VN nền ZKTeco. DB `MITACOSQL`. **Khóa nối chính: `MaChamCong`.**

| Bảng | Vai trò | Cột chính |
|------|---------|-----------|
| `NHANVIEN` | Nhân viên | `MaChamCong` (khóa vân tay), `MaNhanVien` (**= MSNV** khớp bảng lương), `TenNhanVien`, `LoaiNhanVien`, `MaThe`, `CMND`, `MaChucVuNhanVien`, `MaPhongBan`, `MaKhuVuc`, `MaCongTy` |
| `CheckInOut` | **Punch thô** | `MaChamCong`, `GioCham` |
| `CheckInOutTemp` | Punch tạm | |
| `MAYCHAMCONG` | Máy chấm công | |
| `PHONGBAN` / `CHUCVUNHANVIEN` / `KHUVUC` / `CONGTY` | Bộ phận / chức vụ / khu vực / cty | |
| `PHEPNAM` | Phép năm | |
| `KhaiBaoVangChoNhanVien` | Khai báo vắng | |
| `ChiTietDangKyTangCa` | Đăng ký tăng ca | |
| `ChiTietDiCongTac` | Đi công tác | |
| `CHITIETPHUCAPNHANVIEN` / `CHITIETTAMUNGLUONG` / `ChiTietThuongNhanVien` | Phụ cấp / tạm ứng / thưởng | |
| `KYHIEUCHAMCONG` | Ký hiệu chấm công | |
| `TinhCong` (+ proc `TinhCong_getByMaChamCong...`) | **Công đã tính sẵn** | |
| `FINGERTMP` / `FingerTemplate` | Vân tay | |

**Quy tắc đọc (Agent):**
```sql
-- lấy punch kèm MSNV để map sang HRM
SELECT nv.MaNhanVien, io.MaChamCong, io.GioCham
FROM CheckInOut io
JOIN NHANVIEN nv ON nv.MaChamCong = io.MaChamCong
WHERE io.GioCham >= @from AND io.GioCham < @to
```
- Đọc **punch thô `CheckInOut`** để HRM tự tính (minh bạch) **+** đọc `TinhCong` để **đối chiếu chéo**.
- Cột in/out (vào/ra), số máy: **xác nhận trực tiếp trên máy nhà máy có SQLEXPRESS** (backup không đủ để chốt kiểu dữ liệu từng cột).
- ⚠️ Máy dev hiện **chưa cài SQL Server** → không restore được `.BAK` ở đây. Việc xác minh cột chi tiết + viết query cuối làm trên máy Mitapro thật (nơi Agent chạy).

## 4.2 Agent on-prem (DJ Sync Agent)

### Mục tiêu
Cài trên máy Windows **đã có Mitapro + SQL Server**, chạy nền, tự đồng bộ.

### Hành vi

```
[Mitapro SQL] --read-only--> [DJ Agent] --HTTPS JSON--> [DJ HRM API /integrations/mitapro]
```

| Hạng mục | Quy tắc |
|----------|---------|
| Lịch sync | **Tự động** (mặc định cuối ngày + mỗi N phút — Admin cấu hình) |
| Đồng bộ tay | Nút “Đồng bộ ngay” trên Web (ô Chấm Công / Cấu Hình) |
| Bảo mật | Agent có `agent_token`; chỉ push, không nhận lệnh phá hủy DB |
| UI Agent | Icon khay hệ thống: xanh = OK, vàng = đang sync, đỏ = lỗi |
| Log | Mọi lần sync ghi `sync_jobs` (số bản ghi, lỗi tiếng Việt) |

### Dữ liệu tối thiểu mỗi punch / ngày

- `MaNhanVien` (= MSNV, lấy qua JOIN `NHANVIEN`) — map sang `employees.employee_code`
- `GioCham` (punch_time; suy ra vào/ra)
- `MaChamCong`, số máy (optional)
- Ngày làm việc suy ra: first_in, last_out, late_minutes, early_leave_minutes, ot_minutes (**giữ theo phút, full precision**)

### Mapping
- `employee_map`: `NHANVIEN.MaNhanVien` (MSNV) ↔ `employees.employee_code`. Khóa nội bộ Mitapro là `MaChamCong`.
- `dept_map`: `PHONGBAN` (Mitapro) ↔ `departments` (HRM); dùng `departments.mitapro_names[]`.

## 4.3 Giờ làm chuẩn (seed — Admin sửa)

| Ca | Giá trị |
|----|---------|
| Sáng | 08:00–12:00 |
| Chiều | 13:00–17:00 |
| Nghỉ trưa | 12:00–13:00 (không tính công) |
| OT thường | sau 17:00 → ~20:00 |
| Đêm | 22:00–06:00 |

**Đi trễ:** `first_in` > giờ vào chuẩn (+ grace phút — Admin, seed 0 hoặc 5).  
**Về sớm:** `last_out` < giờ về chuẩn (trừ OT đã đăng ký nếu có).

## 4.3b Đơn từ nghỉ phép / OT — **MVP: nhập tay**

> ĐÃ CHỐT: MVP **không** làm workflow duyệt đơn nhiều cấp. Đơn giản, đủ dùng:

- NV chấm công/HR **nhập tay** ngày nghỉ (chọn `leave_code` + số ngày) và **giờ OT** cho từng NV trong ô Chấm Công, trước khi khóa kỳ.
- Nguồn giờ vào/ra vẫn lấy tự động từ Agent Mitapro; đơn nghỉ/OT là lớp **điều chỉnh thủ công** đè lên.
- Mỗi lần nhập/sửa ghi log (ai nhập, khi nào). **Workflow duyệt online để Phase 2** nếu thực sự cần.

## 4.4 Loại ngày nghỉ (Leave catalog)

| Code | Tên | Cty trả lương? | Tính nghỉ không phép? | Ghi chú |
|------|-----|----------------|----------------------|---------|
| `AL` | Phép năm | Có | Không | Cộng vào paid_days |
| `REM` | Nghỉ chế độ NN | **Không** (BH có thể trả) | **Không** | Thai sản, ốm BHXH… |
| `UL` | Phép không lương | Không | Không (đã duyệt) | Ảnh hưởng chuyên cần theo policy |
| `UA` | Không phép | Không | **Có** | Ảnh hưởng chuyên cần |
| `SICK` | Nghỉ bệnh | Theo policy | Không phép? theo doc | Seed: trừ chuyên cần |
| `MARRIAGE` / `FUNERAL` / `HEALTHCHECK` | Kết hôn / Tang / Khám SK cty | — | Không | Không trừ chuyên cần |

## 4.5 Phép năm (seed doc)

| Thâm niên | Ngày phép / năm |
|-----------|-----------------|
| 1 năm → dưới 5 năm | 14 |
| Mỗi thêm 5 năm liên tục | +1 |
| Dưới 12 tháng | Tương ứng số tháng |

- Thường ≤ 1 ngày phép / tháng; tối đa 5 ngày / lần (cần duyệt).
- Lao động nữ hành kinh: nghỉ 30 phút/ngày, tối đa 3 ngày/tháng hoặc về sớm 1,5 giờ/tháng (policy riêng).

## 4.6 KPI (map file Attendance 2026)

```
monthly_manpower = headcount * param_B3   # B3 trong file mẫu; Admin cấu hình
attendance_rate  = attendants / monthly_manpower

end_hc = begin_hc + recruit - resign
turnover_rate = resign / ((begin_hc + end_hc) / 2)

ot_rate = ot_hours / reference_hours
```

Phân loại Direct / Prod Indirect / Admin Indirect — cấu hình theo bộ phận.

## 4.7 Lịch công ty (Calendar Engine)

Tables: `work_calendar`, `holidays`, `pay_periods`

Mỗi kỳ lương:

```
pay_periods.official_work_days = count_from_calendar(month)
pay_periods.salary_divisor = apply_divisor_rule(official_work_days)
```

HR/Admin **xem** mẫu số auto; chỉ ghi đè khi có ngoại lệ (có log + xác nhận 3 lần nếu ảnh hưởng tiền).

*Tiếp: `05_AI_GEMINI.md`*
