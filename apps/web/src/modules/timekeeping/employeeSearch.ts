/** Lọc MSNV / họ tên trên lưới Chấm công — giữ logic một chỗ. */

export function employeeMatchesQuery(
  row: { employee_code: string; full_name?: string | null },
  query: string,
): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return (
    row.employee_code.toLowerCase().includes(needle) ||
    (row.full_name ?? "").toLowerCase().includes(needle)
  );
}

export function findEmployeeByQuery<T extends { employee_code: string; full_name?: string | null }>(
  rows: T[],
  query: string,
  opts?: { exactOnly?: boolean },
): T | undefined {
  const needle = query.trim();
  if (!needle) return undefined;
  const lower = needle.toLowerCase();
  const exact = rows.find((r) => r.employee_code.toLowerCase() === lower);
  if (exact) return exact;
  if (opts?.exactOnly) return undefined;
  const filtered = rows.filter((r) => employeeMatchesQuery(r, needle));
  return (
    filtered.find(
      (r) => r.employee_code.toLowerCase() === lower || r.employee_code.toLowerCase().startsWith(lower),
    ) ?? filtered[0]
  );
}
