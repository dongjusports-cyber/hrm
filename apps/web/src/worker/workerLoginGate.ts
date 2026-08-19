/**
 * Cổng login công nhân trên điện thoại dùng chung.
 * Cấm tự vào phiên cũ khi mở lại / bấm Trở về — phải thấy tên MSNV rồi chọn.
 */
export type WorkerLoginGate = "credentials" | "confirm-session";

export function workerLoginGate(accessToken: string | null | undefined): WorkerLoginGate {
  return accessToken ? "confirm-session" : "credentials";
}
