import type {
  ColumnMovedEvent,
  ColumnPinnedEvent,
  ColumnResizedEvent,
  ColumnState,
  ColumnVisibleEvent,
  GridApi,
} from "ag-grid-community";

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

/** Lưu / khôi phục layout cột (thứ tự, rộng, ghim, ẩn) — dùng chung nhiều lưới. */
export function createAgGridColumnPrefs(key: string) {
  const persist = (api: GridApi) => saveAgGridColumnState(key, api);
  return {
    restore(api: GridApi) {
      return restoreAgGridColumnState(key, api);
    },
    persist,
    handlers: {
      onColumnMoved: (e: ColumnMovedEvent) => persist(e.api),
      onColumnResized: (e: ColumnResizedEvent) => {
        if (e.finished) persist(e.api);
      },
      onColumnPinned: (e: ColumnPinnedEvent) => persist(e.api),
      onColumnVisible: (e: ColumnVisibleEvent) => persist(e.api),
    },
  };
}
