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

const VI_COLLATOR = new Intl.Collator("vi", { numeric: true, sensitivity: "base" });

function isEmptySortValue(v: unknown): boolean {
  if (v == null) return true;
  if (typeof v === "string") return v.trim() === "";
  return false;
}

function toSortText(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? "" : v.toISOString();
  return String(v);
}

/**
 * A→Z / Z→A theo tiếng Việt (Đ sau D, Ă/Â gần A — không đẩy xuống cuối Unicode).
 * AG Grid tự đảo chiều khi Z→A; isDescending chỉ để ô trống luôn đứng cuối.
 */
export function compareViAz(
  valueA: unknown,
  valueB: unknown,
  _nodeA?: unknown,
  _nodeB?: unknown,
  isDescending?: boolean,
): number {
  const emptyA = isEmptySortValue(valueA);
  const emptyB = isEmptySortValue(valueB);
  if (emptyA && emptyB) return 0;
  if (emptyA) return isDescending ? -1 : 1;
  if (emptyB) return isDescending ? 1 : -1;

  if (typeof valueA === "number" && typeof valueB === "number") {
    if (Number.isNaN(valueA) && Number.isNaN(valueB)) return 0;
    if (Number.isNaN(valueA)) return isDescending ? -1 : 1;
    if (Number.isNaN(valueB)) return isDescending ? 1 : -1;
    return valueA - valueB;
  }
  if (typeof valueA === "boolean" && typeof valueB === "boolean") {
    return Number(valueA) - Number(valueB);
  }
  return VI_COLLATOR.compare(toSortText(valueA), toSortText(valueB));
}

/** defaultColDef chung — không gắn `ColDef` (tránh `field: string` phá lưới typed). */
export const AG_GRID_DEFAULT_COL_DEF = {
  sortable: true,
  resizable: true,
  comparator: compareViAz,
  sortingOrder: ["asc", "desc", null] as ("asc" | "desc" | null)[],
};


