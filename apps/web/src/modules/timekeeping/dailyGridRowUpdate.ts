import type { GridApi } from "ag-grid-community";
import type { AttendanceDayGridRow } from "../../shared/api";

/**
 * Cập nhật 1 dòng sau khi lưu ô — không chạy lại sort/filter.
 * applyTransaction / set rowData sẽ xếp lại theo needs_action · giờ vào,
 * khiến người HR đang sửa nhảy khỏi tầm nhìn.
 */
export function updateDailyGridRowInPlace(
  api: GridApi<AttendanceDayGridRow> | null | undefined,
  merged: AttendanceDayGridRow,
): boolean {
  const node = api?.getRowNode(merged.employee_code);
  if (!node || !api) return false;
  const editingThisRow = (api.getEditingCells() ?? []).some((c) => c.rowIndex === node.rowIndex);
  if (editingThisRow) {
    if (node.data) Object.assign(node.data, merged);
    api.refreshCells({ rowNodes: [node], force: true });
    return true;
  }
  node.updateData(merged);
  return true;
}
