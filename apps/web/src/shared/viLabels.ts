/** Nhãn hiển thị tiếng Việt — giữ từ chuyên dùng: Admin, KPI, AI, OT, AL, REM, ATM. */

export function labelEmpStatus(code: string | null | undefined): string {
  switch ((code || "").toLowerCase()) {
    case "active":
      return "Chính thức";
    case "probation":
      return "Thử việc";
    case "resigned":
      return "Thôi việc";
    case "suspended":
      return "Tạm đình chỉ";
    case "maternity":
      return "Thai sản";
    default:
      return code || "—";
  }
}

export function labelPayChannel(code: string | null | undefined): string {
  switch ((code || "").toUpperCase()) {
    case "ATM":
      return "ATM";
    case "CASH":
      return "Tiền mặt";
    default:
      return code || "—";
  }
}

export function labelDeptCategory(code: string | null | undefined): string {
  switch ((code || "").toLowerCase()) {
    case "direct":
      return "Trực tiếp";
    case "prod_indirect":
      return "Gián tiếp SX";
    case "admin_indirect":
      return "Gián tiếp hành chính";
    default:
      return code || "—";
  }
}

export function labelPeriodStatus(code: string | null | undefined): string {
  switch ((code || "").toLowerCase()) {
    case "open":
      return "Đang mở";
    case "calculating":
      return "Đang tính";
    case "calculated":
      return "Đã tính";
    case "published":
      return "Đã phát hành";
    case "locked":
      return "Đã khóa";
    case "closed":
      return "Đã đóng";
    default:
      return code || "—";
  }
}

export function labelJobStatus(code: string | null | undefined): string {
  switch ((code || "").toLowerCase()) {
    case "success":
      return "thành công";
    case "failed":
    case "error":
      return "thất bại";
    case "running":
      return "đang chạy";
    case "requested":
      return "đã yêu cầu";
    case "partial":
      return "một phần";
    case "pending":
      return "chờ";
    default:
      return code || "—";
  }
}

export function labelUserRole(code: string | null | undefined): string {
  switch ((code || "").toLowerCase()) {
    case "admin":
      return "Admin";
    case "user":
      return "Người dùng";
    default:
      return code || "—";
  }
}
