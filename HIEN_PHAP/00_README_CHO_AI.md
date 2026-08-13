# DJ HRM — HIẾN PHÁP PHẦN MỀM
## File điều hướng cho mọi AI / Developer

> **Đọc file này TRƯỚC.** Đây là bảng mục lục và luật ưu tiên nguồn.
> Phiên bản: **1.1** · Ngày: **2026-08-08** · Chủ sở hữu: **Nguyễn Thanh Thiện (Admin duy nhất cấp hệ thống)**
> Trạng thái: **ĐỦ ĐỂ BẮT ĐẦU CODE (P0)** — còn vài mục chờ Chủ (REM, cột Mitapro trên máy nhà máy) nhưng **không chặn dựng khung**.

---

## ⚠️ ĐỌC TRƯỚC — ĐÃ CÓ BỘ V2 (2026-08-10)

Bộ 00–15 dưới đây là hiến pháp **dựng phần mềm từ số không**, đã hoàn thành vai trò: DJ HRM hiện
chạy được với 26 màn hình, 31 bảng, 22 migration.

**Việc đang làm bây giờ là NÂNG CẤP DJ HRM lên đủ nghiệp vụ thay thế GenusSuite.**
Bộ tài liệu cho việc đó là **20–26**, dựng từ việc giải mã 70 bảng và 148 thủ tục PL/SQL của
phần mềm cũ trong `HIEN_PHAP/GenuSuite HRM/`.

| # | File | Khi nào đọc |
|---|------|-------------|
| **20** | `20_HIEN_PHAP_V2_QUY_TRINH.md` | **Mọi phiên — đọc đầu tiên** |
| 21 | `21_SCHEMA_V2.md` | Phiên đụng cơ sở dữ liệu |
| 22 | `22_QUY_TAC_NGHIEP_VU.md` | Phiên đụng lương hoặc chấm công |
| 23 | `23_UI_MAN_HINH.md` | Phiên đụng giao diện |
| 24 | `24_LO_TRINH_5_DOT.md` | Đầu mỗi đợt |
| **26** | `26_TU_DONG_HOA_VAN_HANH.md` | Job nền, Operations Hub, auto-duyệt, pipeline tháng |

**Bàn giao phiên & báo cáo (đọc trước khi code phiên mới):**

| File | Ngày | Nội dung |
|------|------|----------|
| **`BAN_GIAO_PHIEN_20260812.md`** | **2026-08-12** | **Checklist tổng → phiên chat tiếp theo** |
| `BAO_CAO_UI_UX_20260812_PM.md` | 2026-08-12 | Audit UI/UX §23 — P0 FAB/phụ cấp/toolbar — **chưa sửa code** |
| `BAO_CAO_BUG_FAIL_20260812_PM.md` | 2026-08-12 | Bug P0 lương + phụ cấp; 7 test → 346/346 pass |
| `BAO_CAO_BAN_GIAO_MAY_NHA_20260811_PM.md` | 2026-08-11 | Bàn giao USB / overlay hồ sơ NV |

**Luật ưu tiên khi V1 và V2 mâu thuẫn: V2 thắng.** Bộ V1 vẫn còn hiệu lực ở phần V2 không nhắc
tới — stack công nghệ (06), bảo mật và backup (12), runbook vận hành (15), mẫu báo cáo phiên (08).
Tự động hóa vận hành: file **26** (sau v1.0, trừ 24§6.1).

---

## 0. Luật ưu tiên nguồn (khi xung đột)

Khi các tài liệu mâu thuẫn, áp dụng thứ tự sau (cao → thấp):

1. **Quyết định bằng lời của Chủ phần mềm trong chat Cursor** (mới nhất thắng)
2. **Hiến pháp trong thư mục `HIEN_PHAP/`** (bản tổng hợp chính thức)
3. **`Cách tính lương.docx`** + bảng lương Excel thực tế (nguồn nghiệp vụ lương)
4. **`Công nghệ sử dụng.docx`** (stack kỹ thuật bắt buộc)
5. **Prototype `DJ HRM Prototype .html`** (chỉ tham khảo module; **không** copy UI vũ trụ / Audit Mode)

### Quyết định đã hủy (KHÔNG triển khai)

- ❌ **Chế độ đối phó / Audit Mode** (che lương, giả OT) — đã hủy
- ❌ **AI chat trên điện thoại công nhân** — đã hủy
- ❌ **Hard-code** mọi thông số nghiệp vụ (tiền, %, hệ số, ngày…) vào mã nguồn

---

## 1. Mục tiêu sản phẩm (1 câu)

**DJ HRM** là hệ thống HRM cloud (Web) cho **1 nhà máy ~500 người** (công nhân + văn phòng), đồng bộ chấm công từ **Mitapro (SQL)** qua **Agent on-prem**, tính lương theo **Policy Engine metadata-driven**, công nhân xem/xác nhận/khiếu nại phiếu lương trên mobile; Admin cấu hình mọi thông số; AI Gemini hỗ trợ nhắc việc + rà soát khiếu nại (read-only).

Tên nội bộ cũ trong brief: *SPACESHIP HRM* — dùng **DJ HRM** trên UI.

---

## 2. Danh mục file Hiến pháp (đọc theo thứ tự)

| # | File | Nội dung |
|---|------|----------|
| 00 | `00_README_CHO_AI.md` | File này — điều hướng |
| 01 | `01_VISION_NGUYEN_TAC.md` | Tầm nhìn, vai trò, nguyên tắc vàng |
| 02 | `02_UI_PORTAL_PHAN_QUYEN.md` | Portal 8 ô, Lv1–Lv4, RBAC, Worker Portal |
| 03 | `03_CONG_THUC_LUONG.md` | Toàn bộ công thức lương, PC, OT, BH, chuyên cần |
| 04 | `04_CHAM_CONG_AGENT.md` | Mitapro, Agent sync, lịch, mẫu số, REM/AL |
| 05 | `05_AI_GEMINI.md` | Gemini Pro, nhắc việc, quyền `ai_query`, tối ưu token |
| 06 | `06_CONG_NGHE_KIENTRUC.md` | FastAPI, React, PostgreSQL, Module, Docker |
| 07 | `07_SCHEMA_DATABASE.md` | Schema DB chi tiết |
| 08 | `08_MODULE_API_HOP_DONG.md` | Module map, API, hợp đồng báo cáo phiên |
| 09 | `09_LO_TRINH_PHIEN.md` | Lộ trình phiên làm việc (tránh tràn context) |
| 10 | `10_QUYET_DINH_CHOT.md` | Bảng quyết định cuối + checklist Go-live |
| 11 | `11_YEU_CAU_PHI_CHUC_NANG.md` | Hiệu năng, tài nguyên (vừa đủ) — **đọc trước khi code** |
| 12 | `12_BAO_MAT_BACKUP_VAN_HANH.md` | Bảo mật, backup, deploy — **đọc trước khi code** |
| 13 | `13_TEST_NGHIEM_THU_NGOAI_LE.md` | Làm tròn, test, ngoại lệ — **đọc trước khi code** |
| 14 | `14_DATA_DICTIONARY.md` | Từ điển field (tra cứu) |
| 15 | `15_RUNBOOK_KHONG_IT.md` | Xử lý sự cố cho người không IT |

> **Luật tối cao P11 (Vừa đủ):** không rườm rà, nặng, chậm, phức tạp. Mọi giải pháp cân xứng quy mô **1 nhà máy ~500 người, không IT**. Cấm over-engineering (microservices, K8s, broker nặng… khi chưa cần).

---

## 3. Lệnh bắt buộc cho mọi AI khi nhận task

```
1. Đọc 00 → 10 (hoặc ít nhất 00 + file liên quan task + 10)
2. Không hard-code thông số nghiệp vụ
3. Mọi tiền tệ dùng Decimal
4. Mọi lỗi UI/API trả về tiếng Việt
5. Kết thúc phiên: báo cáo theo mẫu Hợp đồng (file 08)
6. Không commit / không deploy trừ khi Chủ yêu cầu
7. Không thêm Audit Mode / AI trên Worker Portal
8. Tách file theo khoa học lợi ích (P3b / 06§6.6a):
   - Tách khi cô lập domain / giảm ảnh hưởng chéo
   - KHÔNG tách chỉ vì file lớn
   - Tách xong mà tệ hơn (mất ngữ cảnh, sửa 1 bug nhiều file) → bắt buộc không tách
```

---

## 4. Stack tóm tắt (chi tiết ở file 06)

| Lớp | Công nghệ |
|-----|-----------|
| Backend | **Python FastAPI** + SQLAlchemy |
| Frontend | **React (Vite)** + **AG-Grid** + TypeScript |
| DB | **PostgreSQL** |
| Queue/Cache | Redis (khuyến nghị) |
| Deploy | Docker Compose → Win10 local trước → VPS VN |
| AI | **Gemini Pro API** (Google Workspace công ty) |
| Agent | App Windows đọc SQL Mitapro → HTTPS lên API |

---

## 5. Portal 8 ô mặc định (Lv1)

```
1. Tổng Quan    2. Nhân Sự     3. Chấm Công    4. Tính Lương
5. Bảo Hiểm Thuế 6. Báo Cáo/KPI  7. Khiếu Nại    8. Cấu Hình
```

- Ô 8 **Cấu Hình** = tối thượng, **chỉ Admin**
- Metadata: Admin có thể đổi tên / thứ tự / bật tắt ô (không hard-code tên trong UI logic)
- Khiếu nại công nhân = ô 7 (nội bộ) + Worker Portal riêng

---

*Hết file 00. Tiếp theo: `01_VISION_NGUYEN_TAC.md`*
