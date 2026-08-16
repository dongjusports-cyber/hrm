# Ý tưởng — Chấm công máy vân tay + điện thoại song song

**Ngày ghi:** 2026-08-17  
**Trạng thái:** ý tưởng thiết kế — **chưa viết code**  
**Quyết định Chủ:** máy Ronal Jack / Mitapro **giữ nguyên**; điện thoại là nguồn **thêm**, không thay máy.

Tài liệu kỹ thuật hiện tại: `HIEN_PHAP/04_CHAM_CONG_AGENT.md`  
Bảng quyết định: `HIEN_PHAP/10_QUYET_DINH_CHOT.md` §10.4

---

## 1. Mục tiêu

Công nhân **vẫn bấm vân tay** như hiện tại. Cùng lúc có thể **mở điện thoại** (nhận diện gương mặt / chụp mặt) để chấm công. Số giờ gửi về **VPS** (`hrm.dongju-v.com`), gộp với giờ máy, rồi tính công / lương như cũ.

Không bắt buộc mọi người dùng điện thoại ngày một: xưởng vẫn lấy máy làm nguồn chính.

---

## 2. Nguyên tắc — hai vòi, một bồn

```
Máy vân tay  →  Mitapro (SQL .122)  →  Agent  →  VPS  attendance_punches
Điện thoại   →  HTTPS API           →  VPS  attendance_punches
                                              ↓
                                    Engine: vào sớm nhất / ra muộn nhất
```

- Lương chỉ cần **MSNV + giờ bấm**. Không quan tâm bấm bằng ngón hay bằng mặt.
- Điện thoại **không** ghi vào Mitapro (agent chỉ **đọc** SQL, không ghi máy).
- Điện thoại **không** tự tính công / lương. Chỉ gửi giờ; VPS tính.

Bảng `attendance_punches` đã có sẵn:

| Cột | Dùng cho điện thoại |
|-----|---------------------|
| `employee_code` | MSNV |
| `punch_time` | Giờ chấm (múi VN) |
| `source` | `mobile` (máy vẫn là `mitapro`) |
| `device_id` | mã máy / điện thoại |
| `direction` | IN / OUT nếu biết |
| `raw` | GPS, ảnh, điểm khớp mặt… |

Trùng giờ: khóa `(employee_code, punch_time)`.  
Bấm liên tiếp trong **1 phút** (máy + ĐT): engine gom 1 lần — vào lấy mốc sớm, ra lấy mốc muộn.

---

## 3. Ai dùng cái gì

| Người | Nguồn |
|--------|--------|
| Công nhân xưởng | Máy vân tay (nhiều người không rảnh / không có ĐT) |
| Văn phòng, đi ngoài, quên bấm máy | Điện thoại |
| Ca đêm / bảo vệ | Máy + ĐT dự phòng |

---

## 4. Làm theo 3 bước (khi Chủ bảo code)

### Bước 1 — Portal công nhân `/worker` (rẻ, kiểm soát được)

Công nhân **đã có** web phiếu lương trên điện thoại. Thêm nút **Chấm công**:

1. Đăng nhập MSNV (như phiếu lương).
2. Bắt buộc **đúng nhà máy** (GPS trong vòng X mét, hoặc Wi‑Fi xưởng).
3. Chụp mặt → lưu ảnh (HR soi được).
4. Gửi VPS: MSNV + giờ + GPS + `source=mobile`.

Chưa cần AI nhận diện phức tạp. Chặn phần lớn gian: chấm từ nhà, nhờ người lạ (còn ảnh).

### Bước 2 — Khóa máy + chống ảnh in

- Mỗi MSNV gắn **một** điện thoại.
- So khớp với ảnh hồ sơ sẵn có (`trich_xuat_*/photos/{MSNV}.jpg`).
- Kiểm tra người thật (nháy mắt / quay đầu) — không chấm bằng ảnh giấy.

Không tự viết mô hình AI từ đầu (dễ gian, tốn công, 359 người sẽ loạn). Dùng SDK có sẵn hoặc bước 1 đủ dùng trước.

### Bước 3 — (tuỳ chọn) máy Face ở cổng

Máy nhận diện mặt loại nhà xưởng, ghi vào Mitapro như máy vân tay. Không phụ thuộc điện thoại công nhân. Đắt hơn; vận hành giống hiện tại.

---

## 5. Cấm / không làm

- Nhét giờ điện thoại vào SQL Mitapro.
- Chỉ tin Face ID iPhone / vân tay Android: đó là «máy này của chủ máy», **không** phải «đúng mặt MSNV 1514».
- Cho chấm khi đứng ngoài nhà máy (không GPS / không Wi‑Fi xưởng).
- Tính công trên điện thoại.
- Ép cả xưởng bỏ máy vân tay.

Gian hay gặp: ảnh in, nhờ bạn bấm hộ, giả GPS. Bước 1 chặn nếu **đúng chỗ + có ảnh**.

---

## 6. Việc chưa làm (khi code Bước 1)

- API worker: `POST /api/worker/punches` (token công nhân, không dùng `AGENT_TOKEN`).
- Cấu hình tọa độ nhà máy + bán kính (Cấu Hình, không hard-code).
- Lưu ảnh chấm (không commit Git; thư mục trên VPS).
- Lưới Chấm Công: cột nguồn `máy` / `ĐT` để HR phân biệt.
- Test: bấm máy + ĐT trong 1 phút = 1 lần vào; chấm ngoài GPS = từ chối.

**Chưa deploy, chưa đổi DB production** cho đến khi Chủ bảo làm bước 1.
