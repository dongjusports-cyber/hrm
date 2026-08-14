# 09 — Lộ trình phiên làm việc (tránh tràn context)

> Mỗi phiên Cursor = 1 mục tiêu hẹp. Không làm cả dự án trong 1 chat.  
> Chủ phần mềm chỉ đạo → AI thực thi theo Hiến pháp.

## 9.1 Nguyên tắc chia phiên

| Quy tắc | Chi tiết |
|---------|----------|
| 1 phiên ≤ 1 module chính | Ví dụ chỉ Auth, hoặc chỉ Agent |
| Đầu phiên | Đọc `00` + `10` + file liên quan |
| Cuối phiên | Hợp đồng báo cáo (file 08) |
| Không nhảy cóc | Hoàn thành Phase N trước khi mở N+1 trừ khi Chủ lệnh |
| File lớn | Tách PR/commit logic theo module |

## 9.2 Phase & phiên đề xuất

### Phase 0 — Khung xương (Local Docker)
| Phiên | Deliverable |
|-------|-------------|
| P0.1 | Repo + docker-compose (api, web, postgres, redis) |
| P0.2 | FastAPI hello + health + Alembic init |
| P0.3 | React Vite Portal **8 ô** + routing Lv1→Lv2 trống |
| P0.4 | Auth login + RBAC (admin 8, user max 7) + popup từ chối quyền |
| P0.5 | Seed portal_tabs + user Admin |

**Cột mốc:** Mở web thấy 8 ô, login được, click ô không quyền → thông báo tiếng Việt.

### Phase 1 — Cấu Hình & MDM
| Phiên | Deliverable |
|-------|-------------|
| P1.1 | Tab Cấu Hình icon con + Users CRUD + gán quyền |
| P1.2 | Policy package JSON editor + **xác nhận 3 lần** |
| P1.3 | Calendar + auto salary_divisor |
| P1.4 | Employees + Departments + import Excel |
| P1.5 | Worker login stub |

### Phase 2 — Agent & Chấm công
| Phiên | Deliverable |
|-------|-------------|
| P2.1 | API ingest punches + sync_jobs |
| P2.2 | Agent Windows đọc SQL (schema từ BAK) |
| P2.3 | Tính late/early/ot_minutes theo lịch |
| P2.4 | Timesheet tháng + UI Chấm Công |
| P2.5 | AI alerts rule: sync lỗi |

### Phase 3 — Payroll Engine
| Phiên | Deliverable |
|-------|-------------|
| P3.1 | Formula engine: wd_salary + divisor |
| P3.2 | Allowances + chuyên cần penalties |
| P3.3 | OT base SI + rates |
| P3.4 | BHXH/BHYT/BHTN/CD + net |
| P3.5 | Regression Oct/2025 (5 NV → full) |
| P3.6 | AG-Grid bảng lương + publish/lock |

### Phase 4 — Worker & Khiếu nại
| Phiên | Deliverable |
|-------|-------------|
| P4.1 | Worker PWA phiếu lương |
| P4.2 | Confirm + khóa |
| P4.3 | Dispute form → ticket + badge nhắc |
| P4.4 | Module Khiếu Nại inbox |
| P4.5 | Gemini `ai_query` rà soát dispute |

### Phase 5 — Báo cáo & cứng cáp
| Phiên | Deliverable |
|-------|-------------|
| P5.1 | KPI Attendance/OT/Turnover |
| P5.2 | Export ATM/CASH |
| P5.3 | Log hộp đen + backup script |
| P5.4 | Hardening local → chuẩn bị Cloud VPS |

### Phase 6 — Cloud & TNCN
| Phiên | Deliverable |
|-------|-------------|
| P6.1 | Deploy VPS VN + SSL + Agent trỏ cloud |
| P6.2 | TNCN module (Phase 2 nghiệp vụ) |

## 9.3 Definition of Done mỗi Phase

- [ ] Chạy được trên Docker local
- [ ] Lỗi tiếng Việt
- [ ] Không hard-code policy số
- [ ] Decimal tiền
- [ ] Báo cáo phiên đã gửi Chủ
- [ ] Không có Audit Mode / AI trên Worker

## 9.4 Thứ tự ưu tiên nếu thiếu thời gian

1. Portal + Auth + Cấu hình quyền  
2. MDM NV + Policy divisor  
3. Payroll khớp Excel (dù công nhập tay)  
4. Agent Mitapro  
5. Worker confirm/dispute  
6. Gemini  
7. KPI đẹp  



---

## Thiết kế giao diện (luật tối cao)

Phần hiển thị liên quan file này tuân **`25_QUY_TAC_THIET_KE_TOI_CAO.md`**: **chính xác · tiện dụng · không rối mắt · không chừa khoảng trống · tận dụng không gian · ngăn nắp · gọn gàng · đồng đều**.
*Tiếp: `10_QUYET_DINH_CHOT.md`*
