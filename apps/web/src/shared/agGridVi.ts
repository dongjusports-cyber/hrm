/** Nhãn AG-Grid tiếng Việt — tránh hiện chữ Anh trên menu cột / sắp xếp. */
export const AG_GRID_LOCALE_VI: Record<string, string> = {
  sortAscending: "A → Z",
  sortDescending: "Z → A",
  sortUnSort: "Bỏ xếp",
  ariaSortableColumn: "Cột có thể xếp",
  ariaColumnSortedAscending: "Đang xếp A → Z",
  ariaColumnSortedDescending: "Đang xếp Z → A",
  page: "Trang",
  of: "trên",
  noRowsToShow: "Không có dòng nào",
  loadingOoo: "Đang tải…",
  selectAll: "Chọn tất cả",
  searchOoo: "Tìm…",
};

/** Xếp giờ HH:mm — ô trống (chưa chấm) lên đầu khi A→Z, giống Excel. */
export function compareHhmmEmptyFirst(
  valueA: string | null | undefined,
  valueB: string | null | undefined,
  _nodeA: unknown,
  _nodeB: unknown,
  isDescending: boolean,
): number {
  const a = (valueA ?? "").trim();
  const b = (valueB ?? "").trim();
  const emptyA = !a;
  const emptyB = !b;
  if (emptyA && emptyB) return 0;
  if (emptyA) return isDescending ? 1 : -1;
  if (emptyB) return isDescending ? -1 : 1;
  return a.localeCompare(b, "vi");
}
