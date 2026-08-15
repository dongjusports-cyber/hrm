# Báo cáo benchmark API — Danh sách nhân viên (Bước H)

**Hệ thống:** https://hrm.dongju-v.com · **Ngày:** 15/08/2026 · **Quy mô:** 359 NV (Postgres production)  
**Trước khi sửa:** `main` @ `24ae902` · **Sau khi sửa:** `main` @ `f02be75`

> **Bản này thay thế bản đầu tiên cùng ngày.** Bản đầu kết luận sai — xem mục 6.

---

## 1. Kết quả một dòng

`GET /api/employees` đang **ghi sổ phép cho từng NV rồi bị hủy toàn bộ**, lặp lại ở mỗi request. Sau khi tách phần ghi ra khỏi đường đọc: **TTFB 2.734 ms → 377 ms**, số câu SQL **2.170 → 17**, không còn lệnh ghi nào.

| Chỉ số (359 NV, VPS) | Trước | Sau | Thay đổi |
|---|---|---|---|
| TTFB (thời gian server nghĩ) | 2.734 ms | **377 ms** | nhanh **7,3 lần** |
| Câu SQL mỗi request | 2.170 | **17** | giảm **99,2 %** |
| Lệnh ghi (INSERT/UPDATE) mỗi request | 1.076 | **0** | hết |
| Logic server (`list_employees`, Session mới) | 2.749 ms | **224 ms** | nhanh **12 lần** |
| Payload gzip | 45,8 KB | 45,8 KB | không đổi |
| Thời gian tải payload | 5 ms | 6 ms | không đổi |

---

## 2. Mục tiêu và phương pháp

Bước H yêu cầu: sau khi thêm cột **Phép còn**, `GET /api/employees` không chậm hơn **300 ms** ở tầng server (~360 NV).

Bốn phạm vi đo, mỗi phạm vi warmup 2 lần rồi lấy trung vị:

| # | Phạm vi | Trả lời câu hỏi |
|---|---|---|
| A | pytest SQLite (360 NV) | Code có hồi quy không? |
| B | `list_employees()` trong container, **Session mới mỗi lần** | Server tốn bao lâu, bao nhiêu câu SQL? |
| C | HTTPS qua Caddy, đo `time_starttransfer` vs `time_total` | Chậm ở server hay ở mạng/payload? |
| D | Từ máy .123 qua internet | HR ở xa cảm nhận thế nào? |

**Hai điểm phương pháp quyết định** (bản báo cáo đầu thiếu cả hai):

1. **Session mới mỗi lần gọi.** Đo nhiều vòng trên cùng một `Session` sẽ được identity map của SQLAlchemy che, vì từ vòng thứ hai dữ liệu đã nằm trong bộ nhớ. Một HTTP request thật luôn có `Session` mới (`get_db`).
2. **Đếm câu SQL, không chỉ đếm milliseconds.** SQLite trong test nhanh hơn Postgres nhiều lần nên mốc thời gian không phát hiện được N+1; số câu SQL thì phát hiện ngay.

---

## 3. Nguyên nhân gốc

Chuỗi gọi: `list_employees` → `annual_leave_remaining_batch` → `ensure_ledger` (INSERT mỗi NV) và `_sync_accrual_if_needed` → `add_entry` (SELECT kiểm tra trùng + INSERT + UPDATE tổng sổ, mỗi NV).

Nhưng `get_db()` không commit:

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()      # khong commit -> moi INSERT/UPDATE bi huy
```

Vì vậy 718 INSERT + 358 UPDATE mỗi request **đều bị hủy**, và request sau làm lại y nguyên. Bằng chứng: DB production có **0 sổ phép năm 2026 và 0 bút toán** dù hệ thống đã chạy nhiều tháng.

Đây không phải vấn đề hiệu năng mà là **vi phạm nguyên tắc `GET` phải chỉ đọc**. Ngoài chuyện chậm còn hai rủi ro:

- **Sổ phép — nguồn chuẩn theo 22§22.7 — đang trống.** Cột «Phép còn» thực chất là số tính lại mỗi lần xem.
- **Ghi đồng thời.** Nhiều HR mở danh sách cùng lúc sẽ cùng chèn `ensure_ledger`, có nguy cơ trùng khóa hoặc chờ lock, giống lỗi race `ensure_pay_period` đã sửa ở commit `2d3b515`.

---

## 4. Số đo chi tiết

### Trước khi sửa (`24ae902`)

| Phạm vi | p50 | Ghi chú |
|---|---|---|
| A — SQLite, cùng Session | 75 ms | **Không hợp lệ** — Session ấm |
| B — VPS, cùng Session | 226 ms | **Không hợp lệ** — báo "đạt 300 ms" |
| B — VPS, **Session mới** | **2.749 ms** | Số thật; 2.170 câu SQL |
| C — HTTPS trên VPS | 2.826 ms | TTFB 2.734 ms, transfer 5 ms |
| D — máy .123 qua internet | 3.205 ms | Chênh so với C là do mạng |

### Sau khi sửa (`f02be75`)

| Phạm vi | TTFB | Transfer | Tải về | Số dòng |
|---|---|---|---|---|
| `/health` | 64 ms | 0,2 ms | 0,2 KB | — |
| `employees` 0 dòng | 61 ms | 0,3 ms | 0 KB | 0 |
| `employees` 1 dòng | 151 ms | 0,1 ms | 0,9 KB | 1 |
| **`employees` đầy đủ** | **377 ms** | 5,7 ms | 45,8 KB | 359 |
| `employees` đầy đủ, không gzip | 300 ms | 3,9 ms | 559 KB | 359 |

Tầng service (Session mới): **p50 224 ms · 17 SELECT · 0 lệnh ghi**.

Đối chiếu ngưỡng Bước H: **logic server 224 ms — đạt**. Tính cả HTTPS, gzip và proxy thì TTFB 377 ms, cao hơn mốc 300 ms một chút; phần vượt nằm ở serialize và nén, không phải ở DB.

---

## 5. Đã sửa những gì

| # | Thay đổi | File |
|---|---|---|
| 1 | `annual_leave_remaining_batch` chỉ đọc — suy ra phần tích lũy chưa ghi bằng công thức, **kết quả không đổi** so với trước | `attendance/annual_leave_ledger.py` |
| 2 | Thêm `sync_accrual_batch` (đường lệnh): bulk insert + tính lại tổng sổ theo lô | `attendance/annual_leave_ledger.py` |
| 3 | Gọi `sync_accrual_batch` khi **chốt kỳ lương**, thay vì khi xem danh sách | `payroll/service.py` |
| 4 | `_refresh_ledger_summary` tính theo lô, tránh một query mỗi sổ | `attendance/annual_leave_ledger.py` |
| 5 | Hàng rào hồi quy: đếm SQL trên Session mới, chặn mọi lệnh ghi trên `GET` | `tests/test_employees_list_benchmark.py` |
| 6 | Script đo lại trên VPS (TTFB + số query) | `ops/bench_employees_vps.py` |

Hàng rào ở mục 5 là phần quan trọng nhất về lâu dài: nếu ai đó đưa lệnh ghi trở lại đường đọc, test đỏ ngay thay vì chờ HR báo chậm.

**Kiểm chứng:** `pytest` **417 passed**. Giá trị cột «Phép còn» không thay đổi — công thức đọc cho đúng con số như sau khi đã ghi bút toán.

---

## 6. Bản báo cáo đầu tiên sai ở đâu

| Kết luận cũ | Thực tế |
|---|---|
| "Chậm vì JSON lớn (~40 field × 359 NV)" | Payload gzip 45,8 KB, tải mất 5 ms. Không liên quan. |
| "Chậm vì mạng .123 ↔ VPS" | Đo ngay trên VPS vẫn 2.826 ms. Không liên quan. |
| "Bước H đạt, server 226 ms" | 226 ms là số đo trên Session ấm. Session mới: 2.749 ms. |
| "Cần view gọn, Redis cache, phân trang, TanStack Query" | Bốn hướng này chỉ **che** lỗi. Sửa đúng gốc là đủ. |
| "2.000 NV sẽ mất 15–20 giây" | Ước lượng đó dựa trên số đo sai. |

Nguyên nhân sai: đo bằng đồng hồ ở phía client và suy ra nguyên nhân, thay vì tách tầng. Một chỉ số duy nhất đã đủ để loại giả thuyết "JSON/mạng": **TTFB 2.734 ms nhưng transfer chỉ 5 ms**.

---

## 7. Quy mô lớn hơn

Với **359 NV hiện tại**: không cần phân trang, cache hay đổi định dạng dữ liệu.

Chi phí bây giờ gần như tuyến tính và nhẹ (17 query cố định, ~0,6 ms/NV ở tầng serialize). Ước lượng: **2.000 NV → TTFB khoảng 1,2–1,5 giây**. Khi thật sự tới ngưỡng đó thì việc cần làm là **phân trang server-side + AG Grid server row model**, cộng endpoint danh sách gọn tách khỏi hồ sơ đầy đủ. Chưa cần làm bây giờ.

---

## 8. Việc còn lại

- **Sổ phép production vẫn trống** (0 bút toán). Sẽ tự điền ở lần **chốt kỳ lương** kế tiếp, qua `sync_accrual_batch`. Giá trị hiển thị đúng trong cả hai trường hợp; không cần can thiệp gấp.
- **Kiểm tra tay** danh sách NV trên web sau deploy: cột «PC thâm niên» và «Phép còn» phải ra đúng như trước, chỉ nhanh hơn.

---

## Phụ lục — chạy lại

```powershell
# Tren VPS: TTFB + so cau SQL (can ops/vps-root.txt)
python ops\bench_employees_vps.py

# Local: hang rao hoi quy
cd apps\api
.\.venv\Scripts\python -m pytest tests/test_employees_list_benchmark.py -q -s
```

| File | Vai trò |
|---|---|
| `ops/bench_employees_vps.py` | Runner từ máy Windows |
| `ops/bench_employees_http_remote.py` | Đo TTFB vs transfer trên VPS |
| `ops/bench_employees_sql_remote.py` | Đếm SQL trong container (chỉ đọc, rollback) |
| `apps/api/tests/test_employees_list_benchmark.py` | Hàng rào hồi quy |

---

*Lập 15/08/2026 · commit `f02be75`.*
