/**
 * Cổng login công nhân: phiên cũ phải xác nhận tên — không tự vào.
 * Không cho đổi MSNV trên cùng điện thoại (khóa máy).
 */
export type WorkerLoginGate = "credentials" | "confirm-session";

export function workerLoginGate(accessToken: string | null | undefined): WorkerLoginGate {
  return accessToken ? "confirm-session" : "credentials";
}
