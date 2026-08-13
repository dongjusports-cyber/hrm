# 07 — UAT HR 1 tháng (chấm công + tính lương)

> Checklist cho HR — **không** cần hiểu code. Dev chỉ sửa khi HR ghi lỗi có bằng chứng.

---

## Trước khi HR bắt đầu (IT/Chủ — 1 lần)

- [ ] Docker Up · `http://192.168.1.123:5173`
- [ ] `alembic upgrade head`
- [ ] Catalog phụ cấp + migrate PCCC/HSE *(đã chạy)*
- [ ] Agent `.122` chạy nền · tab **Đồng bộ** có log OK
- [ ] Tài khoản: `hr1` / `hr2` hoặc `hr.demo`

**URL đúng:** `http://192.168.1.123:5173` — **không** dùng `localhost` từ máy HR khác.

**Admin:** chỉ Cấu hình — dễ khóa nếu sai mật khẩu 3 lần.

---

## Tuần 1–2 — Chấm công

1. **Chấm Công** → kỳ pilot (vd. **08/2026**)
2. Tab **Đồng bộ** → «Đồng bộ ngay» · kiểm tra nhật ký
3. Tab **Tổng hợp / Bảng ngày** → rà MSNV mẫu  
4. Sửa công: xem **`08_HUONG_DAN_CONG_EXCEL.md`** (sửa web / dán Excel 1 ngày)  
5. Duyệt phép / điều chỉnh nếu cần  
6. HR ký: «Bảng công kỳ X OK / chưa OK»

---

## Tuần 2 — Hồ sơ & phụ cấp

1. **Nhân Sự** → mở hồ sơ
2. Kiểm tra từng dòng phụ cấp: PCCC, HSE, Độc hại, Tay nghề, Khác…
3. Thêm/xóa theo thực tế (mỗi loại một dòng)
4. Điện thoại → **Khác (OTHER)**

---

## Tuần 3 — Tính lương

1. **Tính Lương** → kỳ **08/2026**
2. **Tính lương** (draft)
3. So Genus / Excel:

| MSNV | Kiểm tra |
|------|----------|
| **1519** | Neo 07/2026 thực lãnh **9.682.398** |
| **1604** | Nghỉ giữa kỳ → không có trong lương kỳ |
| **1718** | Nghỉ trước kỳ → không draft payslip |

4. Xuất Excel · ghi NV lệch (MSNV + khoản + số Genus + số DJ)

---

## Tuần 4 — Chốt

- [ ] ≥ **95% NV** khớp Genus (lệch nhỏ Decimal chấp nhận — §13)
- [ ] HR + Chủ ký «Đạt pilot»
- [ ] Mở merge UI V2 theo `05_CHECKLIST_MERGE_SAU_V1.md`

---

## Báo lỗi cho Cursor (mẫu)

```
MSNV: 1234
Kỳ: 08/2026
Khoản: PCCC / chuyên cần / …
Genus: 882.000
DJ HRM: 850.000
Ảnh chụp: (đính kèm)
```

---

## Trong 1 tháng UAT — dev làm gì?

| Việc | Có |
|------|-----|
| Sửa bug có mẫu trên | Có |
| Code UI V2 trên 5174 | Có (song song) |
| Đổi giao diện 5173 | Không |
| Tính năng mới | Không (trừ Chủ duyệt) |

---

*Hết bộ Hiến pháp V2 — quay lại `00_README_V2.md` khi cần.*
