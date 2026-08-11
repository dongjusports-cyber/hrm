/** Ô con Lv2 trong Cấu Hình — file 02§2.4 (tông xẹt tông). */

export type ConfigSection = {
  key: string;
  name: string;
  description: string;
  ready: boolean; // false = placeholder phiên sau
};

export const CONFIG_SECTIONS: ConfigSection[] = [
  {
    key: "policy-package",
    name: "Gói chính sách",
    description: "Biểu mẫu chuyên cần + JSON, duyệt 3 bước",
    ready: true,
  },
  {
    key: "catalogs",
    name: "Danh mục",
    description: "Loại nghỉ · Khoản lương · Lookup hồ sơ",
    ready: true,
  },
  {
    key: "payroll-policy",
    name: "Nhân sự / Lương (JSON)",
    description: "Gói Policy JSON + xác nhận 3 lần",
    ready: true,
  },
  {
    key: "insurance-policy",
    name: "Bảo hiểm thuế",
    description: "Tỷ lệ BH + TNCN trong Policy lương (3 bước)",
    ready: true,
  },
  {
    key: "attendance-policy",
    name: "Chấm công / Kỷ luật",
    description: "Phạt chuyên cần trong Policy lương + lịch giờ chuẩn",
    ready: true,
  },
  {
    key: "calendar",
    name: "Lịch",
    description: "Ngày lễ, tuần làm việc, mẫu số tự động",
    ready: true,
  },
  {
    key: "users",
    name: "Người dùng & quyền",
    description: "Tạo tài khoản, gán tối đa 7 module + AI",
    ready: true,
  },
  {
    key: "departments",
    name: "Bộ phận",
    description: "Thêm / sửa / xóa danh mục tổ-bộ phận",
    ready: true,
  },
  {
    key: "agent",
    name: "Agent Mitapro",
    description: "Xem trạng thái đồng bộ (ô Chấm Công)",
    ready: true,
  },
  {
    key: "ai",
    name: "AI Gemini",
    description: "API key, hạn mức token/ngày",
    ready: true,
  },
  {
    key: "portal-tabs",
    name: "Ô Portal",
    description: "Đổi tên / thứ tự / bật-tắt 8 ô Lv1",
    ready: true,
  },
  {
    key: "organization",
    name: "Tổ chức",
    description: "Bộ phận · tổ · chức vụ · công việc",
    ready: true,
  },
  {
    key: "audit-log",
    name: "Nhật ký / Hộp đen",
    description: "Nhật ký kiểm toán cho AI & Admin",
    ready: true,
  },
  {
    key: "kpi",
    name: "KPI (dự phòng)",
    description: "Ngưỡng cảnh báo chuyên cần / OT / nghỉ việc",
    ready: true,
  },
];
