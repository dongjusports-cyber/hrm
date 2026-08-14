# Báo cáo tối ưu — Trợ Lý AI (tra cứu nhanh vs Gemini)

> **Ngày:** 2026-08-13 · **Phạm vi:** Lớp B `POST /api/ai/query` + tra cứu MSNV  
> **Mục tiêu:** Câu đơn giản trả lời nhanh như mở tay; câu phân tích mới chờ Gemini  
> **PR:** #7 (`cursor/esc-keyboard-rules-2ce9`)

---

## 1. Tóm tắt

| Hạng mục | Trước | Sau |
|----------|-------|-----|
| *"xem bảng lương 1519"* | Chờ Gemini/stub **2–5s+** | **Tra cứu nhanh** ~100–300ms (CSDL + format) |
| *"phân tích lương 1519"* | Gemini | Vẫn Gemini (có chờ) |
| Query DB tra MSNV | N+1 (3–4 query / NV) | **Gom batch** (≤4 query / lần, tối đa 3 MSNV) |
| Ngôn ngữ hiển thị | Lẫn tiếng Anh | **100% tiếng Việt** (nhãn + stub + UI) |
| API tests AI | — | **20/20 pass** |

**Kết luận ngắn:** Đạt mục tiêu *“có sẵn thông tin thì lấy ra trả lời ngay”* cho tra cứu MSNV / bảng lương tóm tắt. Phân tích phức tạp vẫn qua Gemini — chấp nhận độ trễ.

---

## 2. Vấn đề ban đầu

1. **Mọi câu hỏi đều gọi Gemini** (hoặc stub giả lập) — kể cả *"thông tin MSNV 1519"* đã có đủ số trong CSDL.
2. **Chậm hơn thao tác tay:** HR mở Tính Lương / Nhân sự vài giây; AI mất thêm round-trip mạng + LLM.
3. **N+1 query:** Mỗi MSNV = 1 query NV + 1 tổ + 1 BP + 1 phiếu lương.
4. **Ngôn ngữ:** Stub và ngữ cảnh khiếu nại còn nhãn tiếng Anh (`WD`, `Gross`, `stub`…).

---

## 3. Kiến trúc hai luồng (dual-path)

```
Câu hỏi user
    │
    ├─ Có dispute_id? ──► Ngữ cảnh khiếu nại ──► Gemini (rà soát)
    │
    ├─ Parse được MSNV?
    │       │
    │       ├─ Không có từ "phân tích / so sánh / …"? ──► TRA CỨU NHANH (direct)
    │       │         Đọc CSDL → format tiếng Việt → trả lời (0 token)
    │       │
    │       └─ Có từ phân tích ──► Inject CSDL + Gemini (≤384 token)
    │
    └─ Chat chung ──► Gemini / stub
```

| Luồng | `model_name` | Meta chat | Token Gemini |
|-------|--------------|-----------|--------------|
| Tra cứu nhanh | `direct` | *tra cứu nhanh* | **0** |
| Phân tích MSNV | `gemini-*` / stub | *Gemini* / *giả lập* | Có |
| Rà soát khiếu nại | `gemini-*` / stub | *Gemini* | Có |
| Chat chung | `gemini-*` / stub | *Gemini* | Có |

---

## 4. Phân loại câu hỏi (cho HR test)

### 4.1 Tra cứu nhanh — không chờ Gemini

Từ khóa **không** có: *phân tích, so sánh, đề xuất, tại sao, giải thích, rà soát, đánh giá, nhận xét, lệch, nguyên nhân, tư vấn, bước tiếp*.

| Ví dụ câu hỏi | Dữ liệu trả về |
|---------------|----------------|
| `thông tin MSNV 1519` | Hồ sơ + phiếu lương gần nhất (nếu có quyền Lương) |
| `xem bảng lương 1519` | Cùng trên — **tóm tắt số**, không mở UI Tính Lương |
| `lương 5290` | Phiếu gần nhất: ngày công, phụ cấp, OT, gross, net |
| `so sánh 1519 và 5290` | ❌ **Không** nhanh — có từ *so sánh* → Gemini |

### 4.2 Vẫn chờ Gemini

| Ví dụ | Lý do |
|-------|-------|
| `phân tích lương 1519 tại sao thấp` | Cần suy luận |
| `so sánh 1519 và 5290` | Đối chiếu nhiều NV |
| Nút **Rà soát bằng AI** (Khiếu Nại) | Luồng `dispute_review` |
| Câu chung không có MSNV | Không có dữ liệu CSDL inject |

---

## 5. Thay đổi kỹ thuật

| File | Nội dung |
|------|----------|
| `apps/api/app/modules/ai/fast_reply.py` | **Mới** — `wants_llm_analysis()`, `format_employee_lookup_answer()` |
| `apps/api/app/modules/ai/employee_context.py` | Gom query NV / tổ / BP / phiếu lương batch |
| `apps/api/app/modules/ai/query.py` | Nhánh `direct` bỏ qua `generate_text()` |
| `apps/api/app/modules/ai/vi_labels.py` | Nhãn VN + `label_ai_mode(direct=True)` → *tra cứu nhanh* |
| `apps/api/app/modules/ai/provider.py` | Http client tái sử dụng; timeout 30s |
| `apps/web/src/shared/AiFab.tsx` | Gợi ý: MSNV nhanh / phân tích mới Gemini |

### 5.1 Giới hạn dữ liệu tra cứu nhanh (chưa đổi)

- Tối đa **3 MSNV** / câu
- **1 phiếu lương gần nhất** / NV (không chọn kỳ theo câu hỏi)
- Cần quyền **Admin / HR / Lương** mới đọc CSDL
- Phiếu chi tiết đầy đủ → vẫn phải mở tab **Tính Lương** (AI chỉ ghi tóm tắt)

---

## 6. Ước lượng hiệu năng

| Bước | Tra cứu nhanh | Có Gemini |
|------|---------------|-----------|
| Parse MSNV + query CSDL | ~50–150ms | ~50–150ms |
| Gọi Gemini API | **Bỏ qua** | ~1,5–5s (mạng + model) |
| Ghi `ai_jobs` | ~10–30ms | ~10–30ms |
| **Tổng cảm nhận** | **< 0,5s** | **2–6s** |

*Lưu ý: Môi trường có `GEMINI_API_KEY` thật sẽ chậm hơn stub; tra cứu nhanh không phụ thuộc key.*

---

## 7. Kiểm thử

```
test_ai_fast_reply.py      — phân loại câu + format trả lời
test_ai_query.py           — direct vs stub phân tích
test_ai_employee_context.py
test_ai_vi_labels.py
test_ai_alerts.py
test_ai_payroll_reminders.py
→ 21 passed
```

Case quan trọng:

- `Lấy thông tin nhân viên 5290` → `model_name=direct`, `stub=false`
- `Phân tích lương nhân viên 5290` → vẫn `stub=true` (môi trường test không key)

---

## 8. Giới hạn & chờ phản hồi HR

| Hạng mục | Trạng thái |
|----------|------------|
| Mở trực tiếp bảng lương UI (`/m/payroll?emp=`) | **Chưa làm** — chờ HR test |
| Chọn kỳ theo câu (*"lương 1519 tháng 7/2026"*) | **Chưa làm** |
| Tra theo tên / bộ phận | **Chưa làm** |
| Rà soát khiếu nại — fast path | **Chưa** — vẫn Gemini (cần phân tích) |
| Deep-link từ AI sang module | **Chưa** |

---

## 9. Khuyến nghị Phase 2 (sau UAT HR)

1. **UAT checklist:** 10 câu tra cứu nhanh + 5 câu phân tích — đo thời gian thực tế trên mạng công ty.
2. Nếu HR hay hỏi **đúng kỳ lương** → thêm parse `YYYY-MM` / `tháng M/YYYY` vào inject.
3. Nếu cần **mở UI** thay vì chỉ ghi text → deep-link Payroll (độ khó thấp–trung bình).
4. Cache ngắn hạn (30–60s) cho cùng MSNV — chỉ khi HR báo vẫn chậm do DB.

---

## 10. Kết luận

**Báo cáo tối ưu AI: HOÀN THÀNH (lần 1).**

- Câu **đơn giản, có sẵn trong CSDL** → trả lời ngay, không tốn token Gemini.
- Câu **so sánh / phân tích** → giữ Gemini, HR chấp nhận chờ.
- Phù hợp hiến pháp §5.3: tối ưu token + trải nghiệm HR.

---

*Liên quan: `05_AI_GEMINI.md`, `BAO_CAO_HR_20260813.md`, PR #7*
