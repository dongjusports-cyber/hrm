/** Hiển thị tên bộ phận / tổ — không kèm mã số đầu dòng (01, 38…). */

export type OrgListFilter = {
  departmentId: string;
  teamId: string;
};

/** Tiêu đề cột lưới NV theo bộ lọc — một cột, không ghép «Bộ phận › Tổ». */
export function orgColumnHeader(filter: OrgListFilter): string {
  return filter.teamId ? "Tổ" : "Bộ phận";
}

/** Giá trị ô cột org: đã chọn tổ → chỉ tổ; còn lại → chỉ bộ phận. */
export function formatOrgColumnCell(
  deptName: string | null | undefined,
  deptCode: string | null | undefined,
  teamName: string | null | undefined,
  teamCode: string | null | undefined,
  filter: OrgListFilter,
): string {
  if (filter.teamId) {
    return formatOrgName(teamName) || teamCode || "—";
  }
  return formatOrgName(deptName) || deptCode || "—";
}

export function formatOrgName(name: string | null | undefined): string {
  if (!name) return "";
  const trimmed = name.trim();
  const stripped = trimmed.replace(/^\d+[\s.\-—–·]*\s*/, "").trim();
  return stripped || trimmed;
}

export function formatDeptTeam(
  deptName: string | null | undefined,
  deptCode: string | null | undefined,
  teamName?: string | null,
  teamCode?: string | null,
): string {
  const dept = formatOrgName(deptName) || deptCode || "—";
  const team = formatOrgName(teamName) || teamCode;
  return team ? `${dept} › ${team}` : dept;
}

export function formatDepartmentLabel(d: { name: string }): string {
  return formatOrgName(d.name) || d.name;
}

export function formatTeamLabel(
  t: { name: string; department_name?: string | null },
  opts?: { showDepartment?: boolean },
): string {
  const team = formatOrgName(t.name) || t.name;
  if (opts?.showDepartment && t.department_name) {
    const dept = formatOrgName(t.department_name) || t.department_name;
    return `${dept} › ${team}`;
  }
  return team;
}

export function isOrgUnitActive(item: { is_active?: boolean }): boolean {
  return item.is_active !== false;
}

const VI_LABEL = new Intl.Collator("vi", { numeric: true, sensitivity: "base" });

/** A→Z tiếng Việt theo tên hiển thị (bỏ mã số đầu dòng). */
export function sortByViName<T extends { name?: string | null }>(rows: T[]): T[] {
  return [...rows].sort((a, b) =>
    VI_LABEL.compare(formatOrgName(a.name) || a.name || "", formatOrgName(b.name) || b.name || ""),
  );
}

export function activeTeams<T extends { is_active?: boolean; name?: string | null }>(teams: T[]): T[] {
  return sortByViName(teams.filter(isOrgUnitActive));
}

export function departmentsWithActiveTeams<
  T extends { id: string; is_active?: boolean; name?: string | null },
>(
  departments: T[],
  teams: { department_id: string; is_active?: boolean }[],
): T[] {
  const activeDeptIds = new Set(
    activeTeams(teams).map((t) => t.department_id),
  );
  return sortByViName(departments.filter((d) => isOrgUnitActive(d) && activeDeptIds.has(d.id)));
}
