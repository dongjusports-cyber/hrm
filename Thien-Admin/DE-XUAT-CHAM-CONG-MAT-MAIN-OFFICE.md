# Đề xuất — Chấm công mặt trên app: hiện cả công ty, chỉ mở Main Office

**Ngày:** 2026-08-17  
**Trạng thái:** đã code giai đoạn 1 (2026-08-17) — chờ deploy khi Chủ/HR chốt GPS nhà máy  
**Chủ đích:** ông Định xem / chốt trước khi làm  
**Nền:** `Y-TUONG-CHAM-CONG-DIEN-THOAI.md` (máy vân tay giữ nguyên; ĐT là nguồn thêm)

---

## Kết luận ngắn

**Làm được.** Cách đúng:

- Mọi người **đều thấy** nút **Chấm công** trên app công nhân.
- Chỉ **Main Office** (mã bộ phận `03`) bấm được.
- Bộ phận khác: nút **mờ**, không gửi được giờ. Máy vân tay vẫn như cũ.
- Khi ông Định bảo test cả xưởng: HR/Admin bật **một công tắc** «Mở cho tất cả» — không phải sửa app từng người.

Khóa phải nằm **trên server**. Chỉ mờ nút trên điện thoại thì người rành máy vẫn gọi API.

---

## Vì sao hiện nút (mờ) chứ không giấu

| Cách | Hệ quả |
|------|--------|
| Giấu nút với xưởng | Người ta nghĩ app không có chấm công; khi mở sau này như tính năng mới, phải giải thích lại |
| Hiện + mờ + dòng chữ | Cả công ty biết đang thử nghiệm văn phòng; xưởng không nhầm là bị cắt vân tay |
| Hiện + bấm được rồi báo lỗi | Phiền, dễ khiếu nại «sao bấm không được» |

Dòng chữ dưới nút mờ (gợi ý):

> Đang thử nghiệm tại Main Office. Bộ phận khác vẫn chấm bằng máy vân tay.

---

## Quy mô thử (snapshot hồ sơ .123)

Không dùng số VPS production (khoảng 359 NV). File snapshot:

| Mã | Bộ phận | Số hồ sơ | App chấm mặt (giai đoạn 1) |
|----|---------|----------|----------------------------|
| 03 | Main Office | 26 | **Mở** |
| 02 | HR & Admin | 16 | Mờ (có thể thêm sau nếu Chủ muốn vòng 1b) |
| 08 | Sewing | 272 | Mờ |
| 06 | Production | 49 | Mờ |
| 01 | Completion | 42 | Mờ |
| 07 | Quality management | 36 | Mờ |
| 09 | Warehouse | 10 | Mờ |
| 04 | Maintenance | 3 | Mờ |

Khóa theo **mã bộ phận `03`**, không theo tên «Main Office» (tên đổi được, mã không).

Người **chuyển tổ** khỏi Main Office: tự mất quyền chấm ĐT (đọc `employees.department_id` lúc bấm). Không phải gỡ tay từng MSNV.

---

## Ba lớp khóa (bắt buộc đủ 3)

```
App ĐT          Hiện nút cho tất cả
                enabled = (mode=all) HOẶC (mode=allowlist VÀ bộ phận ∈ danh sách)
                nếu không: mờ + chữ giải thích — KHÔNG gọi API

API VPS         POST /api/worker/punches
                cùng luật. Ngoài danh sách → 403 tiếng Việt.
                Không tin «nút trên ĐT đã mờ».

Cấu Hình HR     Một bản ghi (không hard-code trong app):
                  mode = off | allowlist | all
                  department_codes = ["03"]     ← giai đoạn 1
                  (tuỳ chọn) extra_msnv = []    ← thử thêm 1–2 người xưởng
```

Khi ông Định chốt test cả cty: `mode = all`. Xưởng sáng hôm sau mở app là bấm được (nếu đã cài PWA / xóa cache một lần nếu SW cũ).

`mode = off`: mọi người đều mờ — dùng khi muốn tạm đóng (lỗi GPS, gian hàng loạt).

---

## Việc chấm mặt (giai đoạn 1 — văn phòng)

Giữ nguyên máy Ronal Jack / Mitapro. Điện thoại **không** ghi SQL máy `.122`.

1. Đăng nhập MSNV (portal `/worker` sẵn có).
2. Server nói «được chấm» hay không (theo cấu hình trên).
3. Nếu được: GPS trong vòng nhà máy **hoặc** Wi‑Fi xưởng; chụp mặt; gửi `source=mobile`.
4. Engine lương: vào sớm nhất / ra muộn nhất — máy + ĐT gộp như đã chốt.

Giai đoạn 1 **chưa cần** AI so khớp mặt phức tạp. Có ảnh + đúng chỗ là HR soi được. So khớp ảnh hồ sơ / chống ảnh in = giai đoạn 2 (khi mở cả xưởng thì mới đáng tiền).

---

## Màn hình Cấu Hình (khi code)

Một trang nhỏ, quyền admin (hoặc HR được ủy quyền):

1. Công tắc lớn: **Thử nghiệm / Mở tất cả / Tắt**
2. Checklist bộ phận (tick Main Office sẵn)
3. Ô MSNV thêm (hiếm dùng)
4. Bán kính GPS + tọa độ nhà máy (không hard-code)

Ông Định / HR không cần kỹ thuật: một tick là xong.

---

## Rủi ro và cách xử

| Rủi ro | Xử |
|--------|----|
| Chỉ mờ UI, API không khóa | Người tự gọi API chấm hộ → **API cùng luật** |
| Khóa theo tên bộ phận | Đổi tên HR → hỏng → khóa **mã `03`** |
| Hai agent / hai app | Một cấu hình trên VPS; app chỉ hỏi `GET /api/worker/me` (thêm `can_mobile_punch`) |
| Main Office đi công tác, GPS nhà máy | Giai đoạn 1: vẫn bắt GPS nhà máy (tránh chấm từ nhà). Công tác = máy vân tay hoặc HR sửa công |
| Mở `all` lúc GPS chưa chắc | Giữ `allowlist` đến khi văn phòng chạy ổn 1–2 tuần |
| PWA cache cũ | Đã sửa `sw.js` v7 network-first; lần mở `all` nhắc xóa data nếu ĐT còn trắng |

---

## Việc chưa làm (khi Chủ bảo code)

Đã làm 2026-08-17:

- Cấu Hình → Chấm công ĐT (`mode` off / allowlist / all, mã bộ phận, MSNV thêm, GPS).
- `GET /api/worker/me` → `can_mobile_punch`, `punch_blocked_reason` (không ghi DB).
- Nút Chấm công trên trang chủ worker: luôn hiện; mờ khi không được.
- `POST /api/worker/punches` — 403 ngoài allowlist; GPS khi đã đặt tọa độ; **không lưu ảnh**, chỉ `photo_hash` + mã `DJ-XXXXXX`.

Còn lại: so khớp AI mặt, cột nguồn máy/ĐT trên lưới HR, deploy VPS + điền GPS nhà máy.

**Chưa deploy production** cho đến khi điền tọa độ nhà máy trên Cấu Hình.
