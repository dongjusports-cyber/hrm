# Hướng dẫn USB + máy công ty (không cần biết code)

> Ngày soạn: **2026-08-11** · Máy nhà: `D:\dj-hrm` · **Chưa có Git/GitHub** trên máy nhà (kiểm tra 2026-08-10).

---

## 1. Đã làm gì? (tóm tắt)

### Đợt 1 — Cây tổ chức → **XONG**
- 438 NV, 73 tổ, 10 bộ phận, chuyển tổ, lưới NV, import GenusSuite (trên **máy nhà** đã chạy lại script — **máy công ty không chạy lại** nếu DB thật còn nguyên).

### Đợt 2 — Danh mục & chính sách → **XONG (code)**
- 2.1 lookup · 2.2 loại nghỉ 14 mã · 2.3 pay_components · 2.4 ca làm việc · 2.5 bảng BH/thuế/thâm niên · 2.6 policy JSON · 2.7 roles · 2.8 Admin Danh mục + Gói chính sách (màn web).

### Đợt 3 — Chấm công → **XONG (code + test)**
- 3.1–3.8: punch, dedupe 60s, tính công, bảng công, duyệt phép, Mitapro sync — **42 test passed**.

### Test máy nhà lần cuối
- **`299+ passed`** (benchmark 1519, seed HĐ, NV thử việc auto TV…).
- **Nghiệm thu tự động:** `docker compose exec api python -m app.scripts.nghiem_thu_hien_phap` — **10 OK** trên DB hiện tại; **1519 = 9.682.398** đã khớp trên DB thật.

### Tiến độ lộ trình (40 mã hiến pháp)
- **Code: ~38/40 mã** có implementation + test.
- **Nghiệm thu tự động: 10/32 tiêu chí** (còn **22 mục HR** bấm thử trên máy công ty).

---

## 2. Nợ / chưa chốt (không chặn copy code)

| Nội dung | Ghi chú |
|----------|---------|
| **Lương tối thiểu vùng** **4.730.000** | Đã chốt với Chủ (2026-08-11); DB backup công ty đã có số này |
| **2.4** ca làm việc | Code có; **nghiệm thu 20.6** trên máy công ty (nếu chưa ký) |
| **DB máy công ty** | Chưa chắc đã `alembic upgrade` tới **`0032`** |
| **GitHub** | Máy nhà **chưa** init git — xem mục 4 bên dưới |
| **Đợt 3.2 trở đi** | **Code xong** — nghiệm thu HR trên máy công ty (Mitapro, Excel, duyệt phép) |

---

## 3. Copy vào USB / ổ cứng di động — copy **cái gì**?

### Khuyến nghị: **copy nguyên cả folder** (an toàn tối ưu)

Bạn có ổ di động, không cần tiết kiệm dung lượng → **copy trọn `D:\dj-hrm\`**, **gồm luôn**:

| Giữ lại (nên copy) | Vì sao |
|--------------------|--------|
| `apps\api\.venv\` | Đúng bộ thư viện Python đã chạy **181 test** — không phụ thuộc mạng công ty lúc đầu |
| `apps\web\node_modules\` | Giao diện chạy ngay, không cần `npm install` (tránh lệch phiên bản) |
| `apps\agent\.venv\` | Agent Mitapro dùng cùng môi trường đã cài sẵn |

Copy một lần:

```text
D:\dj-hrm\   →   (ổ di động)\dj-hrm\
```

Gồm quan trọng:
- `HIEN_PHAP\` — luật + **file này** + `BAO_CAO_BAN_GIAO_MAY_NHA_20260810.md`
- `apps\api\` — backend (code + alembic + **`.venv`**)
- `apps\web\` — giao diện + **`node_modules`**
- `apps\agent\` — Agent Mitapro + **`.venv`** (nếu có)

**Có thể bỏ (chỉ để gọn, không bắt buộc):** `.pytest_cache\`, `dist\`, `__pycache__` — bỏ hay giữ đều không ảnh hưởng an toàn code.

### Lưu ý nhỏ sau khi dán sang máy công ty

- **Đường dẫn khác** (vd. nhà `D:\dj-hrm`, công ty `E:\dj-hrm`): đa số vẫn chạy được. Nếu Python báo lỗi `.venv`, nhờ AI **tạo lại `.venv` một lần** (`pip install -r requirements.txt`) — code trong folder vẫn đúng.
- **`node_modules`** thường copy sang ổ khác **ổn định hơn** `.venv`.

### KHÔNG copy lên ổ/USB **công khai** (vẫn giữ riêng)

- File **`.env`** (mật khẩu DB, JWT, AGENT_TOKEN) — mang kênh riêng hoặc tạo lại trên máy công ty theo IT.  
  *(Nếu chỉ ổ di động cá nhân, bạn **có thể** copy `.env` để mai chạy nhanh — không để lộ cho người khác.)*

### (Tuỳ chọn) USB nhỏ / không muốn nặng

Chỉ khi thiếu chỗ mới **bỏ** `.venv` + `node_modules` và để mai AI chạy `pip install` / `npm install`.

---

## 4. Mai vào công ty — GitHub hay USB?

### Tình trạng hiện tại
- **`D:\dj-hrm` chưa có Git** → **không thể “tải từ GitHub”** trừ khi **tối nay hoặc sáng mai** ai đó đẩy code lên GitHub lần đầu.

### Lựa chọn A — **Chỉ USB** (dễ nhất, không biết code)
1. Copy folder `dj-hrm` (theo mục 3) vào USB.
2. Máy công ty: dán vào ổ (vd. `D:\dj-hrm` hoặc `C:\Projects\dj-hrm`).
3. Mở folder đó bằng **Cursor** (File → Open Folder).
4. Làm các bước mục 5.

### Lựa chọn B — **GitHub** (nên làm sau khi IT có repo)
1. Trên máy nhà (hoặc nhờ IT): tạo repo GitHub, `git init`, push code.
2. Máy công ty: `git clone …` vào thư mục làm việc.
3. Sau này Cloud Agent / Pro chỉ cần **pull** thay vì USB.

**Kết luận:** Mai **chưa có GitHub thì dùng USB**. GitHub là bước **tiếp theo** khi đã clone/push lần đầu.

---

## 5. Mai vào công ty — làm **từng bước** (không cần biết code)

Giả sử đã có code trên máy công ty (USB hoặc GitHub).

### Bước 0 — Mở Cursor đúng folder
- Open folder = thư mục **`dj-hrm`** (có `apps`, `HIEN_PHAP`).

### Bước 1 — Chat AI (quan trọng)
- Mở **chat mới** (New Chat).
- **Dán** toàn bộ file này + `BAO_CAO_BAN_GIAO_MAY_NHA_20260810.md` (hoặc đoạn “Tóm tắt cho AI” ở cuối file này).
- Viết thêm một dòng:  
  `Tiếp tục theo hiến pháp. DB công ty có dữ liệu thật — KHÔNG chạy lại load_org / import_genussuite.`

### Bước 2 — Cập nhật database (nhờ AI hoặc IT chạy lệnh)
Trong terminal, folder `apps\api`:

```text
alembic upgrade head
```

→ Áp migration tới **`20260810_0032`** (punch mở rộng, roles, policy…).

**Không** chạy script xóa/nạp lại 438 NV (mục 3 báo cáo bàn giao).

### Bước 3 — Kiểm tra nhanh backend
Trong `apps\api`:

```text
pytest -q
```

Kỳ vọng: gần **181 passed** (có thể lệch vài test nếu thiếu `.env` — AI sẽ sửa).

### Bước 4 — Chạy thử phần mềm (HR nhìn được)
- Nếu đã copy **đủ `.venv` + `node_modules`** → thường **không cần** cài lại; chạy API + web theo README hoặc theo AI.
- Nếu thiếu dependency → AI hướng dẫn `pip install` / `npm install` một lần.
- Đăng nhập Admin, vào **Cấu Hình → Danh mục / Gói chính sách** (đợt 2.8).

### Bước 5 — Việc **chỉ làm trên máy công ty** (không Cloud)
- Xác nhận **438 NV** / tổ / bộ phận vẫn đúng sau migration.
- **Mitapro / Agent** (mạng nội bộ, SQL Server) — test push punch.
- **Hỏi BH** lương tối thiểu vùng.
- **Nghiệm thu** vài dòng trong `24§` đợt 2 (đổi ngưỡng chuyên cần trên Admin → chạy thử lương).

> **2026-08-11:** Công ty dùng **vân tay Ronald Jack + Mitapro** (không còn quẹt thẻ GenusSuite).
> Đã bỏ `timekeeping_card_no`, mẫu in thẻ CC, thuật ngữ «quẹt thẻ» trong UI/code.

### Bước 6 — Code tiếp (Cloud hoặc Cursor Pro tại công ty)
- **Tiếp theo hiến pháp:** **nghiệm thu đợt 3** trên máy công ty → **đối chiếu đợt 4 MSNV 1519** trên DB thật.
- Một phiên = **một mã** hoặc một tiêu chí nghiệm thu có số.

---

## 6. Code trên **Cloud Agent** — những gì?

| Làm trên Cloud | Không thay máy công ty |
|----------------|------------------------|
| 3.2 → 3.8 (chấm công) | |
| 4.1 → 4.10 (lương engine + màn) | |
| 5.1 → 5.9 (hoàn thiện) | |
| Viết test, migration, React | |
| Tạo **Pull Request** trên GitHub | |

| Vẫn trên **máy công ty** | |
|---------------------------|---|
| `alembic upgrade` DB thật | |
| Agent Mitapro, máy chấm | |
| So sánh số với GenusSuite (1519, 5290…) | |
| HR bấm thử (Excel, duyệt phép…) | |

**Ước lượng:** ~**85–90%** khối lượng **lập trình còn lại** → Cloud; ~**10–15%** → máy công ty (DB + tích hợp + nghiệm thu).

**Điều kiện Cloud:** repo trên GitHub + mỗi lần giao **một mã** (vd. “Chỉ 3.2”).

---

## 7. Chat Cursor — copy chat mai sang máy công ty?

| Câu hỏi | Trả lời |
|---------|---------|
| Dán chat cũ vào máy công ty **có nối tiếp** chat máy nhà không? | **Không tự động.** Mỗi máy / mỗi chat = luồng riêng. |
| Dán nội dung chat + file handoff vào **chat mới** công ty? | **Được — nên làm.** AI đọc ngữ cảnh; **không xóa** chat cũ trên máy nhà. |
| Chat cũ trên máy nhà? | Vẫn nằm trên máy nhà (history Cursor máy nhà). |
| Backup chat? | Copy **file này** + `BAO_CAO_BAN_GIAO…` vào USB; hoặc trong Cursor: chọn đoạn chat → copy/paste vào Notepad lưu `.txt`. |

**Khuyến nghị mai:** USB mang 2 file:
1. `HIEN_PHAP\HUONG_DAN_USB_VA_MAY_CONG_TY_20260811.md` (file này)
2. `HIEN_PHAP\BAO_CAO_BAN_GIAO_MAY_NHA_20260810.md`

Mở **New Chat** trên máy công ty → dán: *“Đọc 2 file handoff trong HIEN_PHAP, tiếp tục 3.2…”*

---

## 8. Tóm tắt 1 dòng cho AI (copy-paste chat công ty)

```text
Dự án DJ HRM tại folder dj-hrm. Đã xong đợt 1, đợt 2 (2.1–2.8), đợt 3.1. Migration tới 20260810_0032. pytest 181 passed trên máy nhà. DB công ty có 438 NV thật — KHÔNG chạy load_org_structure / import_genussuite_2026. Nợ: hỏi BH lương tối thiểu vùng 4.960.000. Làm tiếp hiến pháp mã 3.2 only (lọc punch 60 giây). Đọc HIEN_PHAP/24 và HUONG_DAN_USB_VA_MAY_CONG_TY_20260811.md.
```

---

*Hết hướng dẫn USB / máy công ty.*
