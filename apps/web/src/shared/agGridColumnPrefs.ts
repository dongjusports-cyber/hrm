import type { ColumnState, GridApi } from "ag-grid-community";

/** Đọc thứ tự / độ rộng / ghim cột AG Grid từ localStorage. */
export function loadAgGridColumnState(key: string): ColumnState[] | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as ColumnState[]) : null;
  } catch {
    return null;
  }
}

export function saveAgGridColumnState(key: string, api: GridApi): void {
  localStorage.setItem(key, JSON.stringify(api.getColumnState()));
}

/** Khôi phục cột đã lưu. Trả về true nếu có áp dụng được. */
export function restoreAgGridColumnState(key: string, api: GridApi): boolean {
  const state = loadAgGridColumnState(key);
  if (!state?.length) return false;
  api.applyColumnState({ state, applyOrder: true });
  return true;
}
