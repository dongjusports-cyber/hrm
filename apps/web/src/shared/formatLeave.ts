import type { LeaveType } from "./api";

/** Mã không hiện viết tắt trên lưới (chỉ dùng nội bộ). */
const HIDDEN_LEAVE_CODES = new Set(["NON"]);

/** Hiển thị tên nghỉ tiếng Việt thay mã OFF, ALE… */
export function formatLeaveLabel(
  code: string | null | undefined,
  leaves: LeaveType[],
): string {
  if (!code?.trim()) return "";
  const upper = code.trim().toUpperCase();
  if (HIDDEN_LEAVE_CODES.has(upper)) return "";
  const lt = leaves.find((l) => l.code.toUpperCase() === upper);
  return lt?.name?.trim() || "";
}

/** Danh sách mã nghỉ cho HR chọn — bỏ viết tắt khó hiểu. */
export function leaveTypesForPicker(leaves: LeaveType[]): LeaveType[] {
  return leaves.filter((l) => !HIDDEN_LEAVE_CODES.has(l.code.toUpperCase()));
}
