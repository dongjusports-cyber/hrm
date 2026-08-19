import type { ColumnState, GridApi } from "ag-grid-community";
import type { AttendanceDayGridRow } from "../../shared/api";

export type DailyGridSortMode = "default" | "needs_first";

/** Cột sort khi bật «Đang xếp: cần xử lý» — needs_action desc, rồi giờ vào. */
export function needsFirstSortState(): ColumnState[] {
  return [
    { colId: "needs_action", sort: "desc", sortIndex: 0 },
    { colId: "first_in", sort: "asc", sortIndex: 1 },
  ];
}

/** Xếp mặc định lưới ngày — theo giờ vào. */
export function defaultSortState(): ColumnState[] {
  return [{ colId: "first_in", sort: "asc", sortIndex: 0 }];
}

export function applyDailyGridSort(api: GridApi<AttendanceDayGridRow>, mode: DailyGridSortMode) {
  api.applyColumnState({
    state: mode === "needs_first" ? needsFirstSortState() : defaultSortState(),
    defaultState: { sort: null },
  });
}

/** Toggle còn khớp sort hiện tại trên grid không (tránh nút .is-on sai khi user bấm header). */
export function isNeedsFirstSortActive(columnState: ColumnState[]): boolean {
  const sorted = columnState.filter((c) => c.sort).sort((x, y) => (x.sortIndex ?? 0) - (y.sortIndex ?? 0));
  return sorted[0]?.colId === "needs_action" && sorted[0]?.sort === "desc";
}
