# DJ HRM — Định nghĩa hoàn thành v1.0

> Ngày: **2026-08-11** · Chủ: Nguyễn Thanh Thiện

## Quyết định đã chốt

- **Không** nâng cấp UI Modern (Tailwind/shadcn/TanStack…) **trước** khi đóng **v1.0**.
- Stack giữ theo hiến pháp 20§: FastAPI + React Vite + **AG-Grid** + CSS hiện tại.
- Nâng cấp giao diện = **sau v1.0** (phiên riêng).

## v1.0 = gì?

| Đạt | Nội dung |
|-----|----------|
| Code đợt 1–5 | ~40 mã hiến pháp 24§ đã có implementation + test |
| Nghiệm thu tự động | Script `nghiem_thu_hien_phap` — **0 FAIL** trên DB |
| Neo lương | MSNV **1519** kỳ 07/2026 thực lãnh **9.682.398** |
| Vận hành máy nhà | Docker up, login Admin, Portal dùng được |

## Chưa thuộc “code v1.0” — làm trên máy công ty / HR

- 22 mục `SKIP (HR)` còn lại (Mitapro, dán Excel, bấm thử Admin…)
- Agent sync ≥ 7 ngày, regression T10 ≥ 99% (10§ Go-live)
- Backup UTF-8 tên NV nếu còn lỗi font

## Việc tiếp theo (sau khi đóng code v1.0)

1. Checklist Go-live 10§ trên máy công ty  
2. (Tuỳ chọn) Nâng UI Modern — phiên riêng, không đụng engine lương  

*File này chỉ định nghĩa phạm vi — không thay thế 20–24.*


---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
