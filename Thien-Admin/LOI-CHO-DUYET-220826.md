# BÁO CÁO LỖI CHỜ DUYỆT — 22/08/2026

**Phạm vi:** Đọc toàn bộ `Luật/` (00–07) → rà code 3 phân hệ: Nhân sự (MDM), Chấm công, Tính lương.
**Chạy test thật:** Docker local (DB đã kéo VPS về), full suite pytest.
**Chưa sửa bất kỳ dòng code nào.** Anh/chị duyệt mục nào thì mới sửa mục đó.

---

## A. KẾT QUẢ TEST — «đã biết làm việc chưa?»

| Hạng mục | Kết quả |
|---|---|
| Backend pytest | **591 pass / 10 fail / 2 file lỗi collection** |
| ESC keyboard (vitest) | 19/19 pass (đã báo phiên trước) |
| Luật ↔ code | Khớp phần lớn: cổng OT 17:30, phút từ 17:00, 8 hệ số, trần BH 46.8tr, công đoàn 44.100, divisor cap 26, phép năm 14 +1/5 năm, trả phép ÷26, thử việc 85% + PC=0 |

→ **Kết luận:** Phần mềm hoạt động được, tính lương theo luật đúng ở các bước neo (1519 kỳ 07/2026 có test riêng `test_payroll_benchmark_1519`). Nhưng còn lỗi dưới đây.

---

## B. LỖI THẬT — cần duyệt sửa

### [B1] GET /api/employees chậm trở lại — p50 ~3.3 giây (ngưỡng 300ms)
- **Triệu chứng:** Test benchmark fail: `p50 3293ms > 300ms` với 360 NV. Đúng triệu chứng sự cố HR-H002 tháng 8.
- **Khác lần trước:** SQL vẫn sạch (**24 SELECT, 0 ghi**) — lần này KHÔNG phải ghi-on-read.
- **Nguyên nhân gốc (đã profile bằng cProfile trong container):**
  `_employee_photo_file()` chạy **cho từng NV trên mỗi request list**: mỗi NV gọi `Path.resolve()` + `is_file()` + `stat` → ~1.800 lệnh stat đĩa / request = **~2,5s**, cộng `_photo_dir().resolve()` ~1s.
  File: `apps/api/app/modules/mdm/service.py` hàm `_employee_photo_file`, `_safe_file_under`, `_photo_dir`.
- **Gợi ý sửa (chưa làm):** cache thư mục ảnh 1 lần/request; hoặc cột `photo_exists` lưu DB khi upload; hoặc chỉ check ảnh khi xem chi tiết.
- **Lưu ý:** Trên VPS Postgres + đĩa nhanh con số sẽ khác, nhưng bản chất N stat/NV không đổi. Đề xuất đo lại `ops/bench_employees_vps.py` trước và sau khi sửa.

### [B2] Chuỗi test phụ thuộc thứ tự — chạy cả bộ thì fail, chạy riêng thì pass
- `test_cycle_leave::test_cycle_tick_bumps_out_to_shift_end`: chạy trong full suite ra `last_out 00:00` thay vì `17:00`; **chạy riêng PASS**.
- `test_timesheet::test_ingest_rebuilds_only_employees_with_punches`: tương tự — full suite FAIL, chạy riêng PASS.
- **Ý nghĩa:** Có test nào đó rò rỉ state chung (mock chưa khôi phục / dữ liệu seed). Không phải bug nghiệp vụ nhưng **che mất bug thật**: một ngày nào đó fail thật sẽ bị coi là "flaky".
- **Gợi ý:** chạy `pytest -p no:randomly --lf` tách tìm thủ phạm, hoặc thêm fixture reset mock.

### [B3] 2 file test lỗi ngay khi import — cả bộ test bị dừng nếu không ignore
- `tests/test_extract_annual_leave.py`: `Path(__file__).resolve().parents[3]` → **IndexError** (file nằm sâu 2 cấp, parents[3] vượt gốc).
- `tests/test_fill_bank_from_salary.py`: cùng kiểu IndexError.
- **Hậu quả:** CI/chạy full luôn "Interrupted: collection error" — phải nhớ ignore tay.
- **Gợi ý:** đổi thành `parents[2]` hoặc skip-if-missing như các test khác.

### [B4] Test đọc file ngoài repo không có fallback
- `tests/test_import_wt_regimes.py::test_parse_real_xlsx_18_08` — đòi file Excel `/tmp/che_do.xlsx` (tạo tay), không có thì fail cứng.
- `tests/test_extract_annual_leave.py` có skip-if-missing đúng chuẩn — nên áp dụng giống vậy cho B4.

### [B5] GET /reports/kpi + /reports/overview 404 khi chưa có kỳ lương
- `require_pay_period` ném 404 «chưa có kỳ lương…» trên **đường GET** (rule QA-07 chỉ cấm INSERT, không bắt buộc 404).
- Hệ quả thật: trang Overview/KPI của HR trắng kèm thông báo yêu cầu "bấm Tính lương" dù HR chỉ muốn xem báo cáo đầu ca. 4 test đang fail vì hành vi này (`test_todos_57`, `test_hr_uat_matrix`, `test_kpi_thresholds`).
- **Cần quyết định nghiệp vụ:** (a) giữ 404 nhưng front hiển thị thân thiện, hay (b) trả số 0 + cảnh báo "kỳ chưa tổng hợp". Tôi nghiêng về (b) cho overview, giữ 404 cho export.

### [B6] Sổ phép năm: người cũ chuyển năm không có bút toán mở đầu
- `ensure_ledger` tạo sổ mới `opening_balance = 0` — đúng cho NV vào giữa năm.
- Nhưng **người cũ** (vào từ năm trước): phép cuối năm trước (còn lại) không được kéo sang `opening_balance` của năm mới → nếu dùng hết phép tích năm nay, số dư âm tiềm ẩn/không phản ánh phép tồn năm trước.
- Cần anh/chị xác nhận: công ty có cho **chuyển phép sang năm sau** không (luật 05 chưa ghi rõ điểm này)? Nếu không chuyển → không phải lỗi, chỉ cần ghi 1 dòng vào `Luật/05`.

### [B7] Trả tiền phép còn khi nghỉ việc — chỉ hiện số ngày, chưa có dòng tiền
- `preview_resignation` trả `annual_leave_remaining` (ngày) — **không có** trường tiền trả phép.
- Luật 05: `tiền = lương HĐ / 26 × ngày phép còn`. Engine payout (`KIND_PAYOUT`) đã định nghĩa nhưng **chưa có nơi nào gọi/tạo bút toán payout** (grep toàn repo: KIND_PAYOUT chỉ xuất hiện trong ledger).
- **Gợi ý:** thêm 2 cột preview: tiền trả phép (÷26) + nút tạo phiếu thanh toán khi chốt nghỉ. Chờ duyệt.

### [B8] Thâm niên: 2 nguồn tier lệch nhau (DB vs hằng số)
- DB seed (`seed_rates.SENIORITY_RULES` qua bảng tier): 120–191 = 550.000 · 192–251 = 600.000 · 252–371 = 650.000 · ≥372 = 700.000 — **khớp Luật 04**.
- Nhưng `payroll/seed_allowances.SENIORITY_RULES` (dùng khi hồ sơ không resolve được assignment, ví dụ tab hồ sơ + `employee_to_out`): band 180–240 = 600.000, 240–360 = 650.000 — **lệch ranh giới** so với luật (192/252/372).
- Hậu quả hiện tại thấp (phiếu lương dùng assignment/tier DB), nhưng 2 bảng khác nhau trong code là bom nổ chậm. Đề xuất gộp về 1 nguồn.

---

## C. ĐIỂM NGHI NGỜ NHƯNG CHƯA KẾT LUẬN LÀ LỖI (cần user quyết)

| # | Vấn đề | Chi tiết |
|---|---|---|
| C1 | Ngày lễ (HOL) trong tử số phụ cấp | Luật 04: tử số gồm lễ (`HOL`). Code chỉ điền `detail_days_by_category["HOL"]` — nhưng tôi **chưa tìm thấy chỗ nào sinh category HOL** trong aggregate (chỉ ABS_*, WT, OT…). Nếu ngày lễ NV nghỉ nguyên → có thể bị tính vắng/mất chuyên cần hoặc không được cộng tử số. **Cần test 1 tháng có lễ để kết luận.** |
| C2 | CLEANER bấm 16:xx không OT nhưng cũng không "nghỉ" | Engine: CLEANER ra 16:30 → không OT (đúng luật), worked_hours tính trong ca 07–16 (đúng). OK theo tôi — ghi để đối chiếu khi HR thắc mắc. |
| C3 | OT sáng Cooker giờ > 8:00 | `_allocate_morning_ot` cắt `end = min(last_out, 08:00)` — đúng. Nhưng nếu Cooker quên bấm ra (thiếu mốc) → cả ngày 0 công, kể cả OT sáng đủ cổng. Theo luật «thiếu mốc không tính» — đúng luật, nhưng HR cần biết quy ước này. |

## D. TRẠNG THÁI «ĐÃ CÓ TÍNH NĂNG ĐỦ CHƯA / HỖ TRỢ HR»

**Đã có và hoạt động (theo code + test pass):**
- Nhân sự: hồ sơ đầy đủ (phụ cấp, BHXH, người thân/NPT thuế, hợp đồng, thôi việc + tái tuyển, chế độ thai sản/nuôi con 3 loại, nhắc hết hạn trước 3 ngày — `evaluate_wt_regime_reminders`).
- Chấm công: máy + điện thoại + HR chấm tay (có audit), rà soát thiếu punch, tích chu kỳ, khóa kỳ.
- Tính lương: kỳ/divisor/lương ngày/nghỉ 14 mã/OT 8 hệ số/BH+CD/thuế (tắt), phát hành + worker xác nhận, export Genus.
- AI hỗ trợ HR: alerts (phiếu chưa xác nhận, khóa kỳ trễ, regime hết hạn, KPI vượt ngưỡng), todo cards, hỏi đáp chữ Gemini (text).

**Thiếu / yếu (ghi nhận, chưa sửa):**
1. Trả phép khi nghỉ việc: thiếu **tiền** (B7).
2. Nhắc chế độ chỉ bắn đúng `date_to - 3 ngày` — lỡ hôm đó server không chạy evaluate là mất nhắc (đề xuất: bắn mỗi ngày trong 3 ngày cuối, dedupe theo source_ref đã sẵn sàng).
3. Overview/KPI trắng khi chưa có kỳ (B5).
4. Danh sách NV chậm (B1) — ảnh hưởng trải nghiệm HR hàng ngày nhiều nhất.

---

## E. VIỆC ĐÃ LÀM PHIÊN NÀY (không đụng code production)

1. Đọc 8 file `Luật/`. Rà ~25 file engine/service 3 phân hệ.
2. Bật Docker local, chạy full pytest: 591 pass / 10 fail / 2 collection error.
3. Profile cProfile xác định B1 (stat ảnh × 365 NV).
4. Ghi báo cáo này. **Chưa sửa code, chưa commit gì.**

**Đề xuất thứ tự duyệt:** B1 (chậm nhất, HR đau nhất) → B3+B4 (dọn test) → B5 (quyết nghiệp vụ) → B7 (tính năng) → B6 (xác nhận luật) → B8 (gộp nguồn) → B2 (truy flaky).
