# 06 — Quy tắc cho Cursor AI (giai đoạn V2)

---

## Phân loại task

| Loại task | Làm ở đâu | Nhánh |
|-----------|-----------|-------|
| Bug UAT lương/công | `apps/api`, hiếm khi `apps/web` | `main` |
| UI V2 mới | `apps/web-v2` | `feat/ui-v2` |
| Hiến pháp | `HIEN_PHAP_V2/` | `main` hoặc `feat/ui-v2` |
| Seed/migrate data | `apps/api/scripts` | `main` + HR duyệt |

---

## Cấm tuyệt đối (khi UAT đang chạy)

1. Merge `feat/ui-v2` → `main` mà chưa có `05` checklist
2. Cài Tailwind vào `apps/web` (5173)
3. Migration DB phá dữ liệu HR
4. Đổi port 5173 hoặc credential HR đang dùng
5. Feature mới ngoài `04_MAN_HINH_UU_TIEN.md` (trừ Chủ yêu cầu)

---

## Workflow mỗi phiên

```
1. Đọc HIEN_PHAP_V2/00 → file liên quan task
2. Nếu bug UAT → đọc HIEN_PHAP/22, 03, MSNV + kỳ
3. Nếu UI V2 → checkout feat/ui-v2, chỉ sửa web-v2
4. pytest / vitest trước khi báo xong
5. Không commit trừ khi Chủ yêu cầu
```

---

## Báo cáo phiên (ngắn)

- **UAT fix:** MSNV, kỳ, trước/sau số tiền
- **UI V2:** màn nào, port 5174 screenshot mô tả
- **Không** ghi dài báo cáo vào `HIEN_PHAP/` root — dùng `_ARCHIVE/` nếu cần lưu

---

## Tham chiếu nghiệp vụ V1 (khi sửa bug)

| File V1 | Nội dung |
|---------|----------|
| `20_HIEN_PHAP_V2_QUY_TRINH.md` | Quy trình tổng |
| `22_QUY_TAC_NGHIEP_VU.md` | Lương, công, phụ cấp |
| `03_CONG_THUC_LUONG.md` | Công thức |
| `23_UI_MAN_HINH.md` | Pixel UI bản 5173 |

---

*Tiếp: `07_UAT_HR_1_THANG.md`*
