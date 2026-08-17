/** Lọc MSNV / họ tên trên lưới HR — một chỗ, mọi tab AG Grid. */

export function textMatchesQuery(query: string, ...fields: (string | null | undefined)[]): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return fields.some((f) => (f ?? "").toLowerCase().includes(needle));
}

export function employeeMatchesQuery(
  row: { employee_code: string; full_name?: string | null },
  query: string,
): boolean {
  return textMatchesQuery(query, row.employee_code, row.full_name);
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
