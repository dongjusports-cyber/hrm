import { describe, expect, it, vi } from "vitest";
import type { GridApi } from "ag-grid-community";
import type { AttendanceDayGridRow } from "../../shared/api";
import {
  applyDailyGridSort,
  defaultSortState,
  isNeedsFirstSortActive,
  needsFirstSortState,
} from "./dailyGridSort";

describe("needsFirstSortState", () => {
  it("sorts needs_action desc then first_in asc", () => {
    expect(needsFirstSortState()).toEqual([
      { colId: "needs_action", sort: "desc", sortIndex: 0 },
      { colId: "first_in", sort: "asc", sortIndex: 1 },
    ]);
  });
});

describe("defaultSortState", () => {
  it("sorts first_in asc only", () => {
    expect(defaultSortState()).toEqual([{ colId: "first_in", sort: "asc", sortIndex: 0 }]);
  });
});

describe("isNeedsFirstSortActive", () => {
  it("detects needs_action desc as primary sort", () => {
    expect(
      isNeedsFirstSortActive([
        { colId: "first_in", sort: "asc", sortIndex: 1 },
        { colId: "needs_action", sort: "desc", sortIndex: 0 },
      ]),
    ).toBe(true);
  });

  it("returns false for default first_in sort", () => {
    expect(isNeedsFirstSortActive([{ colId: "first_in", sort: "asc", sortIndex: 0 }])).toBe(false);
  });
});

describe("applyDailyGridSort", () => {
  it("applies needs_first column state", () => {
    const api = { applyColumnState: vi.fn() } as unknown as GridApi<AttendanceDayGridRow>;
    applyDailyGridSort(api, "needs_first");
    expect(api.applyColumnState).toHaveBeenCalledWith({
      state: needsFirstSortState(),
      defaultState: { sort: null },
    });
  });

  it("applies default column state", () => {
    const api = { applyColumnState: vi.fn() } as unknown as GridApi<AttendanceDayGridRow>;
    applyDailyGridSort(api, "default");
    expect(api.applyColumnState).toHaveBeenCalledWith({
      state: defaultSortState(),
      defaultState: { sort: null },
    });
  });
});
