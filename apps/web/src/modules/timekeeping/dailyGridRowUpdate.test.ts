import { describe, expect, it, vi } from "vitest";
import type { GridApi, IRowNode } from "ag-grid-community";
import type { AttendanceDayGridRow } from "../../shared/api";
import { updateDailyGridRowInPlace } from "./dailyGridRowUpdate";

function row(code: string): AttendanceDayGridRow {
  return { employee_code: code } as AttendanceDayGridRow;
}

describe("updateDailyGridRowInPlace", () => {
  it("returns false when the grid or row is missing", () => {
    expect(updateDailyGridRowInPlace(null, row("A"))).toBe(false);
    const api = { getRowNode: vi.fn(() => undefined) } as unknown as GridApi<AttendanceDayGridRow>;
    expect(updateDailyGridRowInPlace(api, row("A"))).toBe(false);
  });

  it("uses updateData so sort does not re-run when the row is not being edited", () => {
    const updateData = vi.fn();
    const node = { rowIndex: 4, data: row("A"), updateData } as unknown as IRowNode<AttendanceDayGridRow>;
    const api = {
      getRowNode: vi.fn(() => node),
      getEditingCells: vi.fn(() => []),
      refreshCells: vi.fn(),
    } as unknown as GridApi<AttendanceDayGridRow>;
    const merged = row("A");
    expect(updateDailyGridRowInPlace(api, merged)).toBe(true);
    expect(updateData).toHaveBeenCalledWith(merged);
    expect(api.refreshCells).not.toHaveBeenCalled();
  });

  it("mutates the live row object when HR is still editing another cell on that row", () => {
    const updateData = vi.fn();
    const data = { employee_code: "A", first_in: null } as AttendanceDayGridRow;
    const node = { rowIndex: 4, data, updateData } as unknown as IRowNode<AttendanceDayGridRow>;
    const api = {
      getRowNode: vi.fn(() => node),
      getEditingCells: vi.fn(() => [{ rowIndex: 4 }]),
      refreshCells: vi.fn(),
    } as unknown as GridApi<AttendanceDayGridRow>;
    const merged = { employee_code: "A", first_in: "08:00" } as AttendanceDayGridRow;
    expect(updateDailyGridRowInPlace(api, merged)).toBe(true);
    expect(updateData).not.toHaveBeenCalled();
    expect(data.first_in).toBe("08:00");
    expect(api.refreshCells).toHaveBeenCalledWith({ rowNodes: [node], force: true });
  });
});
