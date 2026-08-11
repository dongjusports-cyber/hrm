/** State truyền khi mở hồ sơ NV từ lưới HR — ESC / nút ← quay đúng lưới nguồn. */
export type HrNavState = {
  hrListBack?: string;
};

export function hrListBackPath(filterKey: string): string {
  return `/m/hr/lists/${filterKey}`;
}
