# 10 — Bảng quyết định chốt (Single Source of Truth)

> AI đọc file này khi nghi ngờ. Cập nhật khi Chủ ra quyết định mới (ghi ngày).

## 10.1 Tổ chức & vận hành

| # | Câu hỏi | Quyết định | Nguồn |
|---|---------|------------|-------|
| 1 | Số nhà máy | 1 | Chat |
| 2 | Quy mô | ~500 (Excel ~330/tháng) | Chat + Excel |
| 3 | Có IT? | Không — Chủ chỉ đạo, AI thực thi | Chat |
| 4 | Ngôn ngữ | Tiếng Việt | Chat |
| 5 | Local trước | Win10 Pro i3 16GB Docker | Công nghệ.docx |
| 6 | Cloud sau | VPS Việt Nam | Chat |

## 10.2 UI & quyền

| # | Quyết định |
|---|------------|
| 1 | Portal **8 ô**, không sidebar |
| 2 | Lv1 portal → Lv2…Lv4 full màn (tối đa 4 cấp) |
| 3 | 8 ô **luôn hiện**; không ẩn/mờ |
| 4 | Không quyền → popup COSMOS AI tiếng Việt |
| 5 | Admin = 8/8; User max **7** module |
| 6 | Ô Cấu Hình chỉ Admin |
| 7 | Quyền phụ `ai_query` |
| 8 | Worker portal riêng `/worker` |
| 9 | Tab Cấu Hình có thể metadata-sửa tên/thứ tự ô |
| 10 | **Không** Audit Mode |

**8 ô seed:** Tổng Quan · Nhân Sự · Chấm Công · Tính Lương · Bảo Hiểm Thuế · Báo Cáo/KPI · Khiếu Nại · Cấu Hình

## 10.3 Lương & công thức

| # | Quyết định |
|---|------------|
| 1 | Kỳ: **01 → cuối tháng**; trả lương ngày **08** tháng sau |
| 2 | Mẫu số: **auto lịch**; rule 27→26 |
| 3 | **Base OT = mức đóng BH + chuyên cần** (= `DS Lương CB.xlsx`). **KHÁC** base khấu trừ BH! Xác minh 99.7% (295/296) |
| 4 | OT: 150% / 200% / 300% + đêm (policy). `ot_hourly = ot_base/divisor/8` |
| 5 | WD = Lương HĐ (hoặc thử việc) / divisor × (worked + AL) |
| 6 | REM: cty không trả lương; không tính không phép |
| 7 | Thử việc theo **ngày ký HĐ** |
| 8 | Mọi thông số → Cấu Hình (không hard-code) |
| 9 | Save tham số tiền: **xác nhận 3 lần** |
| 10 | TNCN: **Phase 2** |
| 11 | Seed chuyên cần: theo `Cách tính lương.docx` (230k; phạt trễ 3–4 lần 50%, ≥5 mất; nghỉ/về sớm theo doc). Gói mùa khác Admin tạo (gồm rule “1 lần 50% / 2 lần 100%, cộng chung” nếu Chủ bật) |
| 12 | Decimal bắt buộc |
| 13 | **Lương đóng BH = TỰ TÍNH** = Lương HĐ + Σ phụ cấp có `include_in_si_base=TRUE` (chức vụ, độc hại, PCCC, tay nghề, thâm niên — giá trị đầy đủ). **KHÔNG** gồm chuyên cần, đi lại, khác. Đã xác minh 320 NV + NV Bảo hiểm xác nhận. File `DS Lương CB.xlsx` chỉ để đối chiếu (= base + chuyên cần) |
| 14 | OT ban đêm/đêm: **tắt mặc định** (chỉ OT ngày thường 150%); bật khi phát sinh |
| 15 | Re-Pay/truy lĩnh: **1 danh mục `other_adjustments` gộp**, không module riêng |
| 16 | Đơn nghỉ/OT MVP: **nhập tay**, không workflow duyệt (Phase 2 nếu cần) |
| 17 | **Đối chiếu T10/2025 (đã chạy):** Phụ cấp/Gross/BHXH/BHYT/BHTN/Công đoàn(44.100)/Net = **100%**; OT = 99.7%; WD ~95% (lệch do GenuiSuite làm tròn số ngày + ngoại lệ REM). Công thức đã nắm chắc |
| 18 | **`worked_days` giữ full precision** (từ phút); Decimal bắt buộc; chỉ tròn ĐỒNG ở bước cuối |
| 19 | **REM — CHỜ CHỦ:** vài NV được trả lương ngày REM (5122, 6300). Chủ sẽ hỏi NV tính lương rồi trả lời. MVP: mặc định REM **không** trả lương; khi có câu trả lời → cập nhật policy |
| 20 | Nguồn bảng lương cũ: **GenuiSuite** (HRM Hàn Quốc, ~2015→nay, còn chạy nhưng chậm). Excel = xuất từ GenuiSuite |
| 21 | **Chuẩn số mới = Decimal chính xác tuyệt đối** — **KHÔNG** bắt chước làm tròn GenuiSuite. GenuiSuite dùng để học logic + phân loại lệch A/B/C (file 13). Lệch vài đồng do làm tròn cũ = chấp nhận |
| 22 | GenuiSuite chỉnh dữ liệu qua **Toad** → DB backend (thường Oracle / có thể SQL Server). **Không tích hợp sống** vào DJ HRM; chỉ dùng Toad/Excel để tra cứu khi cần. Agent chỉ đọc Mitapro |
| 23 | **Tên sản phẩm: DJ HRM** (DongJu). Thư mục/repo: `dj-hrm` (viết thường). UI hiển thị: **DJ HRM**. AI giữ tên **COSMOS AI** |

## 10.4 Chấm công & Agent

| # | Quyết định |
|---|------------|
| 1 | Mitapro SQL read-only qua **Agent** (kiểu AMIS) |
| 2 | Sync **tự động** + nút tay |
| 3 | Giờ chuẩn 8–12 / 13–17 |
| 4 | **Schema Mitapro đã xác minh** (từ .BAK): punch ở `CheckInOut(MaChamCong, GioCham)`; JOIN `NHANVIEN` để lấy `MaNhanVien`(=MSNV). Có sẵn bảng `TinhCong`. Đọc punch thô + đối chiếu `TinhCong` |
| 5 | Xác minh cột in/out + kiểu dữ liệu **trên máy nhà máy có SQLEXPRESS** (máy dev chưa cài SQL Server) |
| 6 | **Ý tưởng 2026-08-17 — chưa code:** máy vân tay + điện thoại **song song**. ĐT gửi MSNV+giờ thẳng VPS (`source=mobile`); không nhét Mitapro; máy vẫn nguồn chính xưởng. Doc: `Thien-Admin/Y-TUONG-CHAM-CONG-DIEN-THOAI.md` |

## 10.5 Worker phiếu lương

| # | Quyết định |
|---|------------|
| 1 | Login **MSNV + mật khẩu** |
| 2 | Xác nhận → **khóa**, không khiếu nại |
| 3 | Khiếu nại: form text, **không AI trên ĐT** |
| 4 | AI nhắc NV tính lương (badge) |
| 5 | User có `ai_query` mới hỏi Gemini rà soát |

## 10.6 AI

| # | Quyết định |
|---|------------|
| 1 | Gemini **Pro** API (Workspace công ty) |
| 2 | Nhắc việc = rule (0đ) |
| 3 | Chat = on-demand + hạn mức |
| 4 | Read-only |
| 5 | Tên: COSMOS AI |

## 10.7 Stack

| # | Quyết định |
|---|------------|
| 1 | FastAPI + SQLAlchemy + PostgreSQL |
| 2 | React Vite + AG-Grid |
| 3 | Docker |
| 4 | Metadata-driven + Modular |
| 5 | Recursive: Snapshot / Anchor / Module map / Báo cáo phiên |
| 6 | **Tách file có điều kiện:** chia nhỏ để trị khi có lợi; **cấm** tách chỉ vì file lớn (P3b, 06§6.6a) |
| 7 | **P11 Vừa đủ (KISS/YAGNI):** không phức tạp/nặng/chậm; cấm over-engineering; giải pháp cân xứng 500 người 1 nhà máy |
| 8 | Làm tròn: Decimal 4 lẻ bước trung gian, làm tròn đồng ở bước cuối, HALF_UP (file 13) |
| 9 | Backup pg_dump hằng ngày, RPO 24h / RTO 4h (file 12) |
| 10 | Hiệu năng: trang <2s, tính lương 500 NV <2 phút (file 11) |
| 11 | AI provider tách rời (đổi Gemini model/API không sửa module nghiệp vụ) — cần xác minh quota Workspace |
| 12 | Admin cấu hình: tiền/tỷ lệ/ngưỡng/lịch/hệ số. **Không** cho nhập SQL/công thức tự do; dùng khối công thức kiểm soát + xem trước |

## 10.8 Đã hủy

- Audit Mode / chế độ đối phó  
- AI trên mobile công nhân  
- Hard-code số nghiệp vụ  
- Sidebar portal  

## 10.8b Rủi ro phải chốt trước Go-live (3 việc quan trọng nhất)

| # | Rủi ro | Vì sao quan trọng | Cách xử lý |
|---|--------|-------------------|------------|
| **R1** | **Công thức lương** — đã đối chiếu, còn ~5% WD lệch do làm tròn nguồn + ngoại lệ REM | Sai 1 công thức = sai lương cả nhà máy | Đã xác minh: phụ cấp/gross/BH/net/CĐ = 100%, OT = 99.7%. Còn lại: (a) engine dùng full-precision số ngày → tự khớp đồng khi tính từ dữ liệu gốc; (b) **HR chốt quy tắc REM**. Phiên regression T10 cuối cùng phải đạt ≥ 99% & mọi lệch giải thích được |
| **R2** | ~~Base BHXH~~ ✅ **ĐÃ CHỐT** | — | Công thức đã xác minh 320 NV + NV Bảo hiểm: `Lương đóng BH = Lương HĐ + Σ phụ cấp có include_in_si_base`. Chỉ cần seed cờ đúng (§3.4). Regression T10 sẽ kiểm lại lần cuối |
| **R3** | **Chất lượng dữ liệu Mitapro** (thiếu punch, map sai tên bộ phận) | Rác đầu vào = công/OT sai | Màn “rà soát công” trước khi khóa kỳ: cảnh báo thiếu punch, cho HR sửa tay (mục 4.3b) |

## 10.9 Checklist Go-live nhà máy

- [ ] Admin tạo user HR + KT + gán quyền  
- [ ] Import đủ NV + phụ cấp; seed cờ `include_in_si_base` đúng (§3.4)  
- [ ] Agent sync ổn định ≥ 7 ngày  
- [ ] **Regression T10/2025 khớp ≥ 99% NV** (R1) — kiểm luôn Lương đóng BH tự tính  
- [ ] Tính thử 1 tháng khớp Excel  
- [ ] 10 công nhân thử Worker PWA  
- [ ] Policy mùa hiện tại đã seed  
- [ ] Backup DB tự động  
- [ ] Gemini key + hạn mức  

## 10.10 Lệnh khởi động cho AI phiên mới

```
Bạn là AI implement DJ HRM.
1) Đọc D:\HRM\HIEN_PHAP\00_README_CHO_AI.md và 10_QUYET_DINH_CHOT.md
2) Đọc thêm file Hiến pháp liên quan task
3) Thực thi đúng stack FastAPI + React Vite + PostgreSQL
4) Không hard-code policy; không Audit Mode; không AI trên Worker
5) Kết thúc: báo cáo theo hợp đồng file 08
Task phiên này: <Chủ điền>
```

---

**Hiến pháp v1.1 — ĐỦ ĐỂ CODE.**  
Còn mở (không chặn P0): REM chờ NV tính lương; cột chi tiết Mitapro xác nhận trên máy SQLEXPRESS.  
Mọi thay đổi sau: sửa file liên quan + thêm dòng Changelog.

### Changelog

| Ngày | Thay đổi | Người |
|------|----------|-------|
| 2026-03-08 | Phát hành v1.0 — tổng hợp chat + Excel + 2 docx | AI + Nguyễn Thanh Thiện |
| 2026-03-08 | Bổ sung P3b + 06§6.6a: tách file theo khoa học lợi ích, không tách vì file lớn | Nguyễn Thanh Thiện |
| 2026-03-08 | Bổ sung P11 (Vừa đủ, chống phức tạp) + chương 11–15 (phi chức năng, bảo mật/backup, test/ngoại lệ, data dictionary, runbook) | Nguyễn Thanh Thiện |
| 2026-08-08 | Đọc & xác minh `DS Lương CB.xlsx` (329 NV) = master mức đóng BHXH; phát hiện base BHXH ≈ Lương CB − chuyên cần 230k. Áp KISS: đơn nghỉ/OT nhập tay (4.3b), OT đêm tắt mặc định, gộp Re-Pay → `other_adjustments`, giới hạn UI 4 cấp, AI giám sát phần mềm dời Phase 2, thêm `resign_date`/lifecycle NV. Thêm mục 10.8b (3 rủi ro R1–R3) | AI + Nguyễn Thanh Thiện |
| 2026-08-08 | **NV Bảo hiểm xác nhận công thức Lương đóng BH** = Lương HĐ + Σ phụ cấp (chức vụ, độc hại, PCCC, tay nghề, thâm niên); KHÔNG gồm chuyên cần/đi lại/khác. Xác minh khớp 320 NV. Chuyển sang **tự tính** (bỏ nhập tay mức BHXH): `si_base_override` mặc định NULL; seed bảng cờ `include_in_si_base` (§3.4). **R2 đã chốt** | AI + NV Bảo hiểm + Nguyễn Thanh Thiện |
| 2026-08-08 | **Đối chiếu toàn bộ bảng lương T10/2025 (331 NV, đến từng đồng).** Sửa lỗi lớn: **base OT = mức đóng BH + chuyên cần** (KHÔNG phải mức đóng BH) — thêm cờ `include_in_ot_base`. Xác nhận: phụ cấp/gross/BH/net = 100%, OT = 99.7%, công đoàn = 44.100đ. Chốt WD dùng full-precision số ngày; ghi nhận ngoại lệ REM cần HR xác nhận. Cập nhật §3.3, §3.4, §3.5, schema | AI + Nguyễn Thanh Thiện |
| 2026-08-08 | **Quét `SQL_mitapro.BAK`** (205MB) → xác minh schema Mitapro: `NHANVIEN`, `CheckInOut(MaChamCong, GioCham)`, `TinhCong`, `PHONGBAN`… Khóa nối `MaChamCong`; `MaNhanVien`=MSNV. Cập nhật §4.1b, §4.2. Máy dev chưa có SQL Server → chốt cột chi tiết trên máy nhà máy | AI + Nguyễn Thanh Thiện |
| 2026-08-08 | **Chốt chiến lược số:** bảng lương = xuất **GenuiSuite** (HRM Hàn ~2015→nay). DJ HRM dùng **Decimal chính xác**, không copy làm tròn cũ. Phân loại lệch A/B/C (file 13). Quyết định #20–21 | Nguyễn Thanh Thiện |
| 2026-08-08 | REM: Chủ nợ câu trả lời — sẽ hỏi NV tính lương. MVP mặc định REM không trả lương; cập nhật sau | Nguyễn Thanh Thiện |
| 2026-08-08 | GenuiSuite dùng **Toad** chỉnh dữ liệu → có DB backend (Oracle/SQL Server). Không kết nối sống vào DJ HRM; tra cứu thủ công khi cần | Nguyễn Thanh Thiện |
| 2026-08-08 | **Chốt tên: DJ HRM** (công ty DongJu). Repo/thư mục `dj-hrm` viết thường; UI viết hoa DJ HRM. COSMOS AI giữ nguyên | Nguyễn Thanh Thiện |
| 2026-08-15 | **Chuyên cần — quy định mới:** trễ ≥2 hoặc sớm ≥2 → 50%; trễ ≥5 hoặc sớm ≥5 hoặc vắng → 0%. Không gộp trễ+sớm. Miễn vắng: ALE/FLE/WED/TMP/OFF. PT khám thai = mất 100% chuyên cần (HR gán mã miễn tay). Không thêm mã quân sự. Ca Cleaner 07–12/13–16, OT từ 17:00. Chế độ về sớm Thai sản/Nuôi con: bảng `employee_wt_regimes`, thủ công hồ sơ, không tính lùi ngày, AI nhắc T−3. Spec kỹ sư: `Thien-Admin/KE-HOACH-KY-SU-2026-08-15.md` | AI + Nguyễn Thanh Thiện |


---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
