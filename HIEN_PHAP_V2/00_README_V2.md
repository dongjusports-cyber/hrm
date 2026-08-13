# DJ HRM — HIẾN PHÁP V2 (hiện hành)

> **Ngày:** 2026-08-13 · **Chủ:** Nguyễn Thanh Thiện  
> **Trạng thái:** Giai đoạn **UAT HR 1 tháng** + **UI V2 song song** (ẩn)

---

## Đọc file này trước

| Thư mục | Vai trò |
|---------|---------|
| **`HIEN_PHAP_V2/`** | **Hiến pháp mới** — UAT, UI V2, quy tắc song song |
| **`HIEN_PHAP/`** | **Hiến pháp V1 (cũ)** — nghiệp vụ lương, công thức, schema; vẫn tham chiếu khi sửa bug |
| **`HIEN_PHAP/_ARCHIVE/`** | Báo cáo phiên, USB, tài liệu một lần — **không** dùng làm luật |

**Luật ưu tiên khi xung đột:**

1. Lời Chủ trong chat (mới nhất)
2. **`HIEN_PHAP_V2/`** (giai đoạn hiện tại)
3. **`HIEN_PHAP/`** file **20–24**, **10**, **03** (nghiệp vụ lương/công)
4. Excel / GenusSuite thực tế

---

## Mục lục V2

| # | File | Khi nào đọc |
|---|------|-------------|
| **01** | `01_NGUYEN_TAC_SONG_SONG.md` | **Luôn** — 5173 UAT vs 5174 UI V2 |
| **02** | `02_LO_TRINH_UI_V2.md` | Code giao diện mới |
| **03** | `03_STACK_UI_V2.md` | Tailwind, shadcn, AG-Grid |
| **04** | `04_MAN_HINH_UU_TIEN.md` | Thứ tự làm màn |
| **05** | `05_CHECKLIST_MERGE_SAU_V1.md` | Sau HR ký nghiệm thu |
| **06** | `06_QUY_TAC_CHO_AI.md` | Mọi phiên Cursor |
| **07** | `07_UAT_HR_1_THANG.md` | HR test chấm công + lương |

---

## Hai luồng song song

```
HR (1 tháng)                    Dev UI V2 (ẩn)
─────────────                   ───────────────
http://IP:5173                  http://IP:5174
apps/web · main                 apps/web-v2 · feat/ui-v2
Chỉ sửa BUG                     Không merge vào main
```

**API chung:** `apps/api` port **8000** — chỉ sửa API khi UAT báo lỗi có bằng chứng.

---

## v1.0 đóng khi nào?

Xem `HIEN_PHAP/V1_0_DINH_NGHIA.md` + `07_UAT_HR_1_THANG.md`:

- HR pilot ≥ 1 kỳ lương
- MSNV **1519** neo **9.682.398** (07/2026)
- `nghiem_thu_hien_phap` 0 FAIL
- Agent Mitapro ổn

**Sau đó:** merge UI V2 theo `05_CHECKLIST_MERGE_SAU_V1.md`.

---

*Tiếp: `01_NGUYEN_TAC_SONG_SONG.md`*
