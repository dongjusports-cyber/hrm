import {
  clearAuth,
  getAccessToken,
  patchAuthUser,
  setAuth,
  type AuthUser,
} from "./authStore";
import { getApiBase } from "./apiBase";
import { cacheInvalidate, cachedFetch, employeesCacheKey } from "./clientCache";

export type PortalTab = {
  key: string;
  name: string;
  description: string;
  sort_order: number;
  enabled: boolean;
  admin_only: boolean;
  allowed: boolean;
};

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const timeout = AbortSignal.timeout(60_000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  const res = await fetch(`${getApiBase()}${path}`, { ...init, headers, signal });
  if (res.status === 401) {
    clearAuth();
  }
  return res;
}

export async function loginRequest(username: string, password: string): Promise<{
  access_token: string;
  user: AuthUser;
}> {
  const res = await fetch(`${getApiBase()}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    signal: AbortSignal.timeout(60_000),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail ?? "Trợ Lý AI: đăng nhập thất bại.");
  }
  setAuth(data);
  return data;
}

export async function fetchMe(): Promise<AuthUser> {
  const res = await apiFetch("/api/auth/me");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail ?? "Trợ Lý AI: không lấy được thông tin tài khoản.");
  }
  return data as AuthUser;
}

export async function changePasswordRequest(
  currentPassword: string,
  newPassword: string,
): Promise<string> {
  const res = await apiFetch("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      (data as { detail?: string }).detail ?? "Trợ Lý AI: đổi mật khẩu thất bại.",
    );
  }
  patchAuthUser({ must_change_password: false });
  return (data as { detail: string }).detail;
}

export async function fetchPortalTabs(): Promise<{ tabs: PortalTab[]; user_full_name: string }> {
  const res = await apiFetch("/api/portal/tabs");
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail ?? "Trợ Lý AI: không tải được danh sách module.");
  }
  const tabs = (data.tabs as PortalTab[])
    .filter((t) => t.enabled)
    .sort((a, b) => a.sort_order - b.sort_order);
  return { tabs, user_full_name: data.user_full_name as string };
}

export type StaffUser = AuthUser & { is_active: boolean; is_locked?: boolean };

export type AssignableModule = {
  key: string;
  name: string;
  assignable_to_user: boolean;
};

async function readError(res: Response): Promise<string> {
  const data = await res.json().catch(() => ({}));
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return first.msg;
  }
  return "Trợ Lý AI: thao tác thất bại.";
}

export type ConfigPortalTab = {
  key: string;
  name: string;
  description: string;
  sort_order: number;
  enabled: boolean;
  admin_only: boolean;
  is_system: boolean;
};

export async function fetchConfigTabs(): Promise<ConfigPortalTab[]> {
  const res = await apiFetch("/api/config/tabs");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function saveConfigTabs(
  tabs: {
    key: string;
    name: string;
    description: string;
    sort_order: number;
    enabled: boolean;
  }[],
): Promise<ConfigPortalTab[]> {
  const res = await apiFetch("/api/config/tabs", {
    method: "PUT",
    body: JSON.stringify({ tabs }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function resetConfigTabs(): Promise<ConfigPortalTab[]> {
  const res = await apiFetch("/api/config/tabs/reset", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchUsers(): Promise<StaffUser[]> {
  const res = await apiFetch("/api/users");
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as StaffUser[];
}

export async function fetchAssignableModules(): Promise<{
  modules: AssignableModule[];
  max_user_modules: number;
}> {
  const res = await apiFetch("/api/users/meta/modules");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createUser(body: {
  username: string;
  full_name: string;
  password: string;
  modules: string[];
  permissions: string[];
  must_change_password: boolean;
}): Promise<StaffUser> {
  const res = await apiFetch("/api/users", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateUser(
  id: string,
  body: {
    full_name?: string;
    is_active?: boolean;
    modules?: string[];
    permissions?: string[];
    new_password?: string;
  },
): Promise<StaffUser> {
  const res = await apiFetch(`/api/users/${id}`, { method: "PUT", body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deactivateUser(id: string): Promise<void> {
  const res = await apiFetch(`/api/users/${id}/deactivate`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
}

export async function unlockStaffUser(id: string): Promise<string> {
  const res = await apiFetch(`/api/users/${id}/unlock`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as { detail?: string };
  return data.detail ?? "Đã mở khóa tài khoản.";
}

export type CatalogLeaveType = {
  code: string;
  name: string;
  paid_by_company: boolean;
  counts_as_unauthorized: boolean;
  pay_ratio_percent: number | null;
  paid_by_si: boolean;
  affects_attendance_bonus: boolean;
  counts_as_worked_day: boolean;
  requires_document: boolean;
  max_days_per_year: number | null;
};

export async function fetchCatalogLeaveTypes(): Promise<CatalogLeaveType[]> {
  const res = await apiFetch("/api/config/catalog/leave-types");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createCatalogLeaveType(body: {
  code: string;
  name: string;
  paid_by_company?: boolean;
  counts_as_unauthorized?: boolean;
  pay_ratio_percent?: number | null;
  paid_by_si?: boolean;
  affects_attendance_bonus?: boolean;
  counts_as_worked_day?: boolean;
  requires_document?: boolean;
  max_days_per_year?: number | null;
}): Promise<CatalogLeaveType> {
  const res = await apiFetch("/api/config/catalog/leave-types", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateCatalogLeaveType(
  code: string,
  body: Partial<Omit<CatalogLeaveType, "code">>,
): Promise<CatalogLeaveType> {
  const res = await apiFetch(`/api/config/catalog/leave-types/${encodeURIComponent(code)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type CatalogPayComponent = {
  id: string;
  code: string;
  name: string;
  kind: string;
  default_amount: string | number;
  proration: string;
  proration_rule: string;
  include_in_si_base: boolean;
  include_in_ot_base: boolean;
  affects_si_base: boolean;
  affects_ot_base: boolean;
  affects_pit: boolean;
  is_active: boolean;
};

export async function fetchCatalogPayComponents(): Promise<CatalogPayComponent[]> {
  const res = await apiFetch("/api/config/catalog/pay-components");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createCatalogPayComponent(body: {
  code: string;
  name: string;
  kind?: string;
  default_amount?: number;
}): Promise<CatalogPayComponent> {
  const res = await apiFetch("/api/config/catalog/pay-components", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateCatalogPayComponent(
  code: string,
  body: Partial<{ name: string; default_amount: number; is_active: boolean }>,
): Promise<CatalogPayComponent> {
  const res = await apiFetch(`/api/config/catalog/pay-components/${encodeURIComponent(code)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type LookupValueRow = {
  id: string;
  group_code: string;
  code: string;
  name: string;
  name_local: string | null;
  sort_order: number;
  is_active: boolean;
};

export async function fetchCatalogLookupValues(groupCode?: string): Promise<LookupValueRow[]> {
  const q = groupCode ? `?group_code=${encodeURIComponent(groupCode)}` : "";
  const res = await apiFetch(`/api/config/catalog/lookup-values${q}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createCatalogLookupValue(body: {
  group_code: string;
  code: string;
  name: string;
  name_local?: string | null;
  sort_order?: number;
}): Promise<LookupValueRow> {
  const res = await apiFetch("/api/config/catalog/lookup-values", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

/** Danh mục lookup hồ sơ — HR đọc (21§21.4). */
export type LookupValue = LookupValueRow;

export async function fetchLookupValues(groupCode: string): Promise<LookupValue[]> {
  const res = await apiFetch(`/api/lookup-values?group_code=${encodeURIComponent(groupCode)}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type EmployeeEducation = {
  id: string;
  employee_id: string;
  from_date: string | null;
  to_date: string | null;
  school_name: string;
  major: string | null;
  degree_code: string | null;
  note: string;
  created_at: string | null;
};

export type EmployeeExperience = {
  id: string;
  employee_id: string;
  from_date: string | null;
  to_date: string | null;
  company_name: string;
  position_title: string | null;
  note: string;
  created_at: string | null;
};

export type EmployeeHealthCheck = {
  id: string;
  employee_id: string;
  check_date: string;
  facility_name: string | null;
  result_summary: string | null;
  note: string;
  created_at: string | null;
};

export async function fetchEmployeeEducations(empId: string): Promise<EmployeeEducation[]> {
  const res = await apiFetch(`/api/employees/${empId}/educations`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createEmployeeEducation(
  empId: string,
  body: Record<string, unknown>,
): Promise<EmployeeEducation> {
  const res = await apiFetch(`/api/employees/${empId}/educations`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateEmployeeEducation(
  empId: string,
  rowId: string,
  body: Record<string, unknown>,
): Promise<EmployeeEducation> {
  const res = await apiFetch(`/api/employees/${empId}/educations/${rowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteEmployeeEducation(empId: string, rowId: string): Promise<void> {
  const res = await apiFetch(`/api/employees/${empId}/educations/${rowId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

// --- Chế độ về sớm (Thai sản / Nuôi con) — 22§22.14 (Bước D) ---

export type WtRegimeType = "PREGNANT" | "MATERNITY" | "CHILD";

export type EmployeeWtRegime = {
  id: string;
  employee_id: string;
  regime_type: WtRegimeType;
  hours_early: number;
  date_from: string;
  date_to: string;
  note: string;
  created_at: string | null;
  ended_at: string | null;
};

export type WtRegimeCreate = {
  regime_type: WtRegimeType;
  hours_early: number;
  date_from: string;
  date_to: string;
  note?: string;
};

export type WtRegimeUpdate = {
  hours_early?: number;
  date_to?: string;
  note?: string;
};

export async function fetchEmployeeWtRegimes(empId: string): Promise<EmployeeWtRegime[]> {
  const res = await apiFetch(`/api/employees/${empId}/wt-regimes`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createEmployeeWtRegime(
  empId: string,
  body: WtRegimeCreate,
): Promise<EmployeeWtRegime> {
  const res = await apiFetch(`/api/employees/${empId}/wt-regimes`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function patchEmployeeWtRegime(
  empId: string,
  regimeId: string,
  body: WtRegimeUpdate,
): Promise<EmployeeWtRegime> {
  const res = await apiFetch(`/api/employees/${empId}/wt-regimes/${regimeId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function endEmployeeWtRegime(
  empId: string,
  regimeId: string,
): Promise<EmployeeWtRegime> {
  const res = await apiFetch(`/api/employees/${empId}/wt-regimes/${regimeId}/end`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchEmployeeExperiences(empId: string): Promise<EmployeeExperience[]> {
  const res = await apiFetch(`/api/employees/${empId}/experiences`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createEmployeeExperience(
  empId: string,
  body: Record<string, unknown>,
): Promise<EmployeeExperience> {
  const res = await apiFetch(`/api/employees/${empId}/experiences`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateEmployeeExperience(
  empId: string,
  rowId: string,
  body: Record<string, unknown>,
): Promise<EmployeeExperience> {
  const res = await apiFetch(`/api/employees/${empId}/experiences/${rowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteEmployeeExperience(empId: string, rowId: string): Promise<void> {
  const res = await apiFetch(`/api/employees/${empId}/experiences/${rowId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

export async function fetchEmployeeHealthChecks(empId: string): Promise<EmployeeHealthCheck[]> {
  const res = await apiFetch(`/api/employees/${empId}/health-checks`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createEmployeeHealthCheck(
  empId: string,
  body: Record<string, unknown>,
): Promise<EmployeeHealthCheck> {
  const res = await apiFetch(`/api/employees/${empId}/health-checks`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateEmployeeHealthCheck(
  empId: string,
  rowId: string,
  body: Record<string, unknown>,
): Promise<EmployeeHealthCheck> {
  const res = await apiFetch(`/api/employees/${empId}/health-checks/${rowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteEmployeeHealthCheck(empId: string, rowId: string): Promise<void> {
  const res = await apiFetch(`/api/employees/${empId}/health-checks/${rowId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

export type LabourContract = {
  id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  contract_type_code: string;
  contract_type_label?: string;
  contract_no?: string;
  times_label?: string;
  seq_no: number;
  sign_date: string | null;
  start_date: string;
  end_date: string | null;
  base_salary: string | number;
  position_code: string | null;
  team_id: string | null;
  status: string;
  file_path: string | null;
  days_until_expiry: number | null;
  created_at: string | null;
};

export type LabourContractRenewPreview = {
  employee_id: string;
  employee_code: string;
  previous_contract_id: string | null;
  previous_contract_type_code: string | null;
  previous_contract_type_label: string | null;
  suggested_contract_type_code: string;
  suggested_contract_type_label: string;
  suggested_seq_no: number;
  suggested_contract_no: string;
  suggested_start_date: string;
  suggested_end_date: string | null;
  suggested_sign_date: string;
  suggested_base_salary: string | number;
  allowed_contract_type_codes: string[];
  message: string;
};

export async function fetchLabourContracts(params: {
  employee_id?: string;
  expiring_within_days?: number;
} = {}): Promise<LabourContract[]> {
  if (params.employee_id) {
    const res = await apiFetch(
      `/api/labour-contracts?employee_id=${encodeURIComponent(params.employee_id)}`,
    );
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  }
  if (params.expiring_within_days != null) {
    const res = await apiFetch(
      `/api/labour-contracts/expiring?within_days=${params.expiring_within_days}`,
    );
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  }
  const res = await apiFetch("/api/labour-contracts");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createLabourContract(body: Record<string, unknown>): Promise<LabourContract> {
  const res = await apiFetch("/api/labour-contracts", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchLabourContractRenewPreview(
  employeeId: string,
): Promise<LabourContractRenewPreview> {
  const res = await apiFetch(
    `/api/labour-contracts/renew-preview?employee_id=${encodeURIComponent(employeeId)}`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function renewLabourContract(body: {
  employee_id: string;
  contract_type_code?: string;
  sign_date?: string | null;
  start_date?: string;
  end_date?: string | null;
  base_salary?: string | number;
}): Promise<LabourContract> {
  const res = await apiFetch("/api/labour-contracts/renew", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateLabourContract(
  id: string,
  body: Record<string, unknown>,
): Promise<LabourContract> {
  const res = await apiFetch(`/api/labour-contracts/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteLabourContract(id: string): Promise<void> {
  const res = await apiFetch(`/api/labour-contracts/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

export type EmployeeFamilyMember = {
  id: string;
  employee_id: string;
  relationship_code: string;
  full_name: string;
  birth_date: string | null;
  id_number: string | null;
  is_tax_dependent: boolean;
  dependent_from: string | null;
  dependent_to: string | null;
  is_effective: boolean;
  created_at: string | null;
};

export type TaxDependents = {
  employee_id: string;
  as_of_date: string;
  effective_count: number;
  members: EmployeeFamilyMember[];
};

export async function fetchFamilyMembers(empId: string): Promise<EmployeeFamilyMember[]> {
  const res = await apiFetch(`/api/employees/${empId}/family-members`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchTaxDependents(empId: string, asOf?: string): Promise<TaxDependents> {
  const q = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  const res = await apiFetch(`/api/employees/${empId}/tax-dependents${q}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createFamilyMember(
  empId: string,
  body: Record<string, unknown>,
): Promise<EmployeeFamilyMember> {
  const res = await apiFetch(`/api/employees/${empId}/family-members`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateFamilyMember(
  empId: string,
  memberId: string,
  body: Record<string, unknown>,
): Promise<EmployeeFamilyMember> {
  const res = await apiFetch(`/api/employees/${empId}/family-members/${memberId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteFamilyMember(empId: string, memberId: string): Promise<void> {
  const res = await apiFetch(`/api/employees/${empId}/family-members/${memberId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readError(res));
}

export type EmployeeResignation = {
  id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  seq_no: number;
  resign_type_code: string;
  applied_date: string | null;
  last_working_date: string;
  reason: string | null;
  severance_months: number;
  severance_amount: string | number;
  handover_done: boolean;
  rehired_at: string | null;
  created_at: string | null;
};

export async function fetchResignations(empId: string): Promise<EmployeeResignation[]> {
  const res = await apiFetch(`/api/employees/${empId}/resignations`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createResignation(
  empId: string,
  body: Record<string, unknown>,
): Promise<EmployeeResignation> {
  const res = await apiFetch(`/api/employees/${empId}/resignations`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type ResignationPreview = {
  employee_id: string;
  employee_code: string;
  full_name: string;
  resign_type_code: string;
  last_working_date: string;
  tenure_years: number;
  severance_months: number;
  severance_amount: string | number;
  annual_leave_remaining: string | number;
  account_will_lock: boolean;
};

export async function fetchResignationPreview(
  empId: string,
  resignTypeCode: string,
  lastWorkingDate: string,
): Promise<ResignationPreview> {
  const qs = new URLSearchParams({
    resign_type_code: resignTypeCode,
    last_working_date: lastWorkingDate,
  });
  const res = await apiFetch(`/api/employees/${empId}/resignation-preview?${qs.toString()}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type HrMovement = {
  id: string;
  movement_type: string;
  occurred_at: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  summary: string;
  value_before: string | null;
  value_after: string | null;
  decision_no: string | null;
  approved_by_name: string | null;
};

export async function fetchHrMovements(params: {
  employee_id?: string;
  limit?: number;
} = {}): Promise<HrMovement[]> {
  const qs = new URLSearchParams();
  if (params.employee_id) qs.set("employee_id", params.employee_id);
  if (params.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  const res = await apiFetch(`/api/hr/movements${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type InsuranceDeclaration = {
  id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  si_book_no: string | null;
  declaration_type: string;
  declaration_type_label: string;
  effective_month: string;
  old_salary: string | number;
  new_salary: string | number;
  reason_code: string | null;
  batch_no: string | null;
  submitted_at: string | null;
  status: string;
  created_at: string | null;
};

export async function fetchInsuranceDeclarations(params: {
  effective_month?: string;
  status?: string;
} = {}): Promise<InsuranceDeclaration[]> {
  const qs = new URLSearchParams();
  if (params.effective_month) qs.set("effective_month", params.effective_month);
  if (params.status) qs.set("status", params.status);
  const q = qs.toString();
  const res = await apiFetch(`/api/insurance/declarations${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function proposeInsuranceDeclarations(
  effectiveMonth: string,
): Promise<{ created_count: number; items: InsuranceDeclaration[] }> {
  const res = await apiFetch(`/api/insurance/declarations/propose/${effectiveMonth}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function downloadInsuranceDeclarationBatch(
  effectiveMonth: string,
  declarationIds?: string[],
): Promise<void> {
  const qs = new URLSearchParams({ effective_month: effectiveMonth });
  if (declarationIds?.length) {
    declarationIds.forEach((id) => qs.append("declaration_ids", id));
  }
  const res = await apiFetch(`/api/insurance/declarations/export/download?${qs.toString()}`);
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `bhxh_${effectiveMonth}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function markInsuranceDeclarationsSubmitted(body: {
  effective_month?: string;
  batch_no?: string;
  declaration_ids?: string[];
}): Promise<{ marked: number; message: string }> {
  const res = await apiFetch("/api/insurance/declarations/mark-submitted", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type TodoCard = {
  key: string;
  title: string;
  body: string;
  count: number;
  target_module: string;
  href: string;
  priority: number;
};

export async function fetchTodos(): Promise<{ cards: TodoCard[]; total: number }> {
  const res = await apiFetch("/api/ai/todos");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export function printEmployeeContractUrl(empId: string, contractId?: string): string {
  const q = contractId ? `?contract_id=${encodeURIComponent(contractId)}` : "";
  return `${getApiBase()}/api/print/employees/${empId}/contract${q}`;
}

export function printEmployeeDecisionUrl(empId: string, decisionNo?: string): string {
  const q = decisionNo ? `?decision_no=${encodeURIComponent(decisionNo)}` : "";
  return `${getApiBase()}/api/print/employees/${empId}/decision${q}`;
}

export function printEmployeeProbationUrl(empId: string, contractId?: string): string {
  const q = contractId ? `?contract_id=${encodeURIComponent(contractId)}` : "";
  return `${getApiBase()}/api/print/employees/${empId}/probation${q}`;
}

/** Mở mẫu in HTML trong tab mới (kèm JWT). */
export async function openPrintHtml(path: string): Promise<void> {
  const res = await apiFetch(path);
  if (!res.ok) throw new Error(await readError(res));
  const html = await res.text();
  const w = window.open("", "_blank");
  if (!w) throw new Error("Trình duyệt chặn cửa sổ mới.");
  w.document.write(html);
  w.document.close();
}

export async function printEmployeeContract(empId: string, contractId?: string): Promise<void> {
  const q = contractId ? `?contract_id=${encodeURIComponent(contractId)}` : "";
  await openPrintHtml(`/api/print/employees/${empId}/contract${q}`);
}

export async function printEmployeeDecision(empId: string, decisionNo?: string): Promise<void> {
  const q = decisionNo ? `?decision_no=${encodeURIComponent(decisionNo)}` : "";
  await openPrintHtml(`/api/print/employees/${empId}/decision${q}`);
}

export async function printEmployeeProbation(empId: string, contractId?: string): Promise<void> {
  const q = contractId ? `?contract_id=${encodeURIComponent(contractId)}` : "";
  await openPrintHtml(`/api/print/employees/${empId}/probation${q}`);
}

export async function printSalaryRaiseAppendix(body: {
  scope: "all" | "department" | "employees";
  department_code?: string;
  employee_ids?: string[];
  target: "contract_salary" | "probation_salary" | "allowance";
  allowance_code?: string;
  amount: string;
  effective_from?: string;
}): Promise<void> {
  const res = await apiFetch("/api/print/salary-raise", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  const html = await res.text();
  const w = window.open("", "_blank");
  if (!w) throw new Error("Trình duyệt chặn cửa sổ mới.");
  w.document.write(html);
  w.document.close();
}

export type OrgSummary = {
  departments: number;
  teams: number;
  positions: number;
  jobs: number;
  active_departments: number;
  active_teams: number;
};

export async function fetchOrgSummary(): Promise<OrgSummary> {
  const res = await apiFetch("/api/config/org/summary");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type OrgTeam = {
  id: string;
  code: string;
  name: string;
  name_local: string | null;
  department_id: string;
  department_code: string | null;
  department_name: string | null;
  default_shift_id: string | null;
  is_active: boolean;
};

export type WorkShiftRow = {
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  lunch_deduct_hours: string | number;
  standard_hours: string | number;
  is_active: boolean;
};

export type TeamShiftScheduleRow = {
  id: string;
  team_id: string;
  team_code: string;
  work_date: string;
  work_shift_id: string;
  note: string;
};

export async function fetchOrgTeams(): Promise<OrgTeam[]> {
  const res = await apiFetch("/api/config/org/teams");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function patchTeamDefaultShift(
  teamId: string,
  defaultShiftId: string,
): Promise<OrgTeam> {
  const res = await apiFetch(`/api/config/org/teams/${teamId}/default-shift`, {
    method: "PATCH",
    body: JSON.stringify({ default_shift_id: defaultShiftId }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchCatalogWorkShifts(): Promise<WorkShiftRow[]> {
  const res = await apiFetch("/api/config/catalog/work-shifts");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchTeamShiftSchedules(params: {
  team_id?: string;
  date_from?: string;
  date_to?: string;
}): Promise<TeamShiftScheduleRow[]> {
  const qs = new URLSearchParams();
  if (params.team_id) qs.set("team_id", params.team_id);
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await apiFetch(`/api/config/catalog/team-shift-schedules${suffix}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function upsertTeamShiftSchedule(body: {
  team_id: string;
  work_date: string;
  work_shift_id: string;
  note?: string;
}): Promise<TeamShiftScheduleRow> {
  const res = await apiFetch("/api/config/catalog/team-shift-schedules", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type PolicyPackage = {
  id: string;
  name: string;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  version: number;
  payload: Record<string, unknown>;
};

export type PolicyConfirmPreview = {
  step: number;
  status: "need_confirm" | "saved" | string;
  detail: string;
  changed_money_fields: string[];
  package: PolicyPackage | null;
};

export async function fetchPolicyPackages(): Promise<PolicyPackage[]> {
  const res = await apiFetch("/api/policies/packages");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updatePolicyPackage(
  id: string,
  body: { name?: string; payload: Record<string, unknown> },
  confirmStep: number,
): Promise<PolicyConfirmPreview> {
  const res = await apiFetch(`/api/policies/packages/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
    headers: { "X-Confirm-Step": String(confirmStep) },
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type DivisorInfo = {
  year: number;
  month: number;
  official_work_days: string | number;
  salary_divisor: string | number;
  divisor_rule: Record<string, unknown>;
  work_weekdays: number[];
  holidays_in_month: Holiday[];
  policy_package_name: string | null;
  detail: string;
};

export type Holiday = { date: string; name: string };

export type WorkWeek = {
  id: number;
  work_weekdays: number[];
  morning_start: string;
  morning_end: string;
  afternoon_start: string;
  afternoon_end: string;
  grace_late_minutes: number;
};

export async function fetchDivisor(year: number, month: number): Promise<DivisorInfo> {
  const res = await apiFetch(`/api/calendar/divisor?year=${year}&month=${month}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchWorkWeek(): Promise<WorkWeek> {
  const res = await apiFetch("/api/calendar/work-week");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateWorkWeek(body: {
  work_weekdays: number[];
}): Promise<WorkWeek> {
  const res = await apiFetch("/api/calendar/work-week", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchHolidays(year?: number): Promise<Holiday[]> {
  const q = year ? `?year=${year}` : "";
  const res = await apiFetch(`/api/calendar/holidays${q}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function addHoliday(body: { date: string; name: string }): Promise<Holiday> {
  const res = await apiFetch("/api/calendar/holidays", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteHoliday(day: string): Promise<void> {
  const res = await apiFetch(`/api/calendar/holidays/${day}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(await readError(res));
}

export type Department = {
  id: string;
  code: string;
  name: string;
  category: string;
  mitapro_names: string[];
  is_active?: boolean;
};

export type Team = {
  id: string;
  code: string;
  name: string;
  name_local: string | null;
  department_id: string;
  department_code: string | null;
  department_name: string | null;
  is_active: boolean;
};

export type Employee = {
  id: string;
  employee_code: string;
  full_name: string;
  gender: string | null;
  birth_date?: string | null;
  birth_place_code?: string | null;
  nationality_code?: string | null;
  ethnicity_code?: string | null;
  religion_code?: string | null;
  marital_status?: string | null;
  children_count?: number;
  education_code?: string | null;
  id_number: string | null;
  id_issue_date?: string | null;
  id_issue_place_code?: string | null;
  permanent_address?: string | null;
  temporary_address?: string | null;
  urgent_contact?: string | null;
  si_book_no?: string | null;
  bank_account: string | null;
  pay_channel: string;
  department_id: string | null;
  department_code: string | null;
  department_name: string | null;
  team_id: string | null;
  team_code: string | null;
  team_name: string | null;
  position_code: string | null;
  position_title: string | null;
  join_date: string | null;
  contract_signed_at: string | null;
  probation_salary: string | number;
  contract_salary: string | number;
  allowance_total?: string | number;
  total_salary?: string | number;
  si_base_override: string | number | null;
  si_enrolled: boolean;
  pit_enrolled?: boolean;
  tax_dependent_count?: number;
  seniority_label?: string | null;
  seniority_amount?: string | number | null;
  annual_leave_remaining?: string | number | null;
  contract_type_label?: string;
  status: string;
  effective_status?: string;
  status_label?: string;
  resign_date: string | null;
  phone: string | null;
  has_photo?: boolean;
  photo_url?: string | null;
  account_status?: "active" | "locked" | "resigned";
  account_status_label?: string;
  is_locked?: boolean;
  failed_attempts?: number;
  has_worker_account?: boolean;
  wt_regime_active?: boolean;
  wt_regime_type?: string | null;
  wt_regime_date_from?: string | null;
  wt_regime_date_to?: string | null;
  si_base?: string | number | null;
};

export type UnlockResetPasswordResult = {
  detail: string;
  employee_id: string;
  employee_code: string;
  account_status: "active" | "locked" | "resigned";
  account_status_label: string;
};

export async function fetchDepartments(): Promise<Department[]> {
  const res = await apiFetch("/api/departments");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createDepartment(body: {
  code: string;
  name: string;
  category: string;
}): Promise<Department> {
  const res = await apiFetch("/api/departments", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateDepartment(
  id: string,
  body: { name?: string; category?: string; mitapro_names?: string[] },
): Promise<Department> {
  const res = await apiFetch(`/api/departments/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteDepartment(id: string): Promise<void> {
  const res = await apiFetch(`/api/departments/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

export async function fetchTeams(): Promise<Team[]> {
  const res = await apiFetch("/api/teams");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type Position = {
  code: string;
  name: string;
  name_local: string | null;
  level: number | null;
  is_management: boolean;
  sort_order: number;
  is_active: boolean;
};

export async function fetchPositions(): Promise<Position[]> {
  const res = await apiFetch("/api/positions?active_only=true");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type EmployeeFilters = {
  q?: string;
  status?: string;
  department_id?: string;
  team_id?: string;
};

function employeeFiltersToQuery(filters: EmployeeFilters): string {
  const qs = new URLSearchParams();
  if (filters.q) qs.set("q", filters.q);
  if (filters.status && filters.status !== "all") qs.set("status", filters.status);
  if (filters.department_id) qs.set("department_id", filters.department_id);
  if (filters.team_id) qs.set("team_id", filters.team_id);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export async function fetchEmployees(filters: EmployeeFilters = {}): Promise<Employee[]> {
  const key = employeesCacheKey(filters);
  return cachedFetch(key, async () => {
    const res = await apiFetch(`/api/employees${employeeFiltersToQuery(filters)}`);
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  });
}

/** Xuất Excel — đúng cột đang hiện (view Gọn/Đầy đủ) + đúng bộ lọc đang bật (23§ Xuất Excel). */
export async function downloadEmployeesExport(
  filters: EmployeeFilters,
  columns: string[],
): Promise<void> {
  const qs = new URLSearchParams();
  if (filters.q) qs.set("q", filters.q);
  if (filters.status && filters.status !== "all") qs.set("status", filters.status);
  if (filters.department_id) qs.set("department_id", filters.department_id);
  if (filters.team_id) qs.set("team_id", filters.team_id);
  if (columns.length) qs.set("columns", columns.join(","));
  const res = await apiFetch(`/api/employees/export?${qs.toString()}`);
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(cd);
  a.download = match ? match[1] : "danh_sach_nv.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

export async function fetchEmployee(id: string): Promise<Employee> {
  const res = await apiFetch(`/api/employees/${id}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createEmployee(body: Record<string, unknown>): Promise<Employee> {
  const res = await apiFetch("/api/employees", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await readError(res));
  const row = (await res.json()) as Employee;
  cacheInvalidate("employees:");
  return row;
}

export type ValidationIssue = {
  field: string;
  code: string;
  level: "error" | "warn" | "info";
  message: string;
  meta?: Record<string, unknown> | null;
};

export type EmployeeValidateResult = {
  ok: boolean;
  issues: ValidationIssue[];
  error_count: number;
  warn_count: number;
  suggested_code?: string | null;
};

export async function suggestEmployeeCode(): Promise<string> {
  const res = await apiFetch("/api/employees/suggest-code");
  if (!res.ok) throw new Error(await readError(res));
  const body = (await res.json()) as { suggested_code: string };
  return body.suggested_code;
}

export async function validateEmployee(body: {
  is_new: boolean;
  employee_id?: string;
  payload: Record<string, unknown>;
}): Promise<EmployeeValidateResult> {
  const res = await apiFetch("/api/employees/validate", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type EmployeeRehireResult = {
  employee: Employee;
  rehire_mode: string;
  message: string;
};

export async function rehireEmployee(
  employeeId: string,
  body: {
    rehire_date: string;
    rehire_mode: "fresh_start" | "continuity";
    rehire_reason?: string;
    team_id: string;
    status: "active" | "probation";
    contract_salary?: string;
    probation_salary?: string;
  },
): Promise<EmployeeRehireResult> {
  const res = await apiFetch(`/api/employees/${employeeId}/rehire`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as EmployeeRehireResult;
  cacheInvalidate("employees:");
  return data;
}

export async function updateEmployee(id: string, body: Record<string, unknown>): Promise<Employee> {
  const res = await apiFetch(`/api/employees/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  const row = (await res.json()) as Employee;
  cacheInvalidate("employees:");
  return row;
}

export async function unlockResetWorkerPassword(
  employeeId: string,
): Promise<UnlockResetPasswordResult> {
  const res = await apiFetch(`/api/employees/${employeeId}/unlock-reset-password`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type BulkSalaryRaisePreview = {
  scope: string;
  department_code: string | null;
  department_name: string | null;
  target: string;
  target_label: string;
  allowance_code: string | null;
  amount: string | number;
  affected_count: number;
  message: string;
};

export type BulkSalaryRaiseResult = {
  scope: string;
  department_code: string | null;
  target: string;
  target_label: string;
  allowance_code: string | null;
  amount: string | number;
  affected_count: number;
  message: string;
};

export async function previewSalaryRaise(body: {
  scope: "all" | "department" | "employees";
  department_code?: string;
  employee_ids?: string[];
  target: "contract_salary" | "probation_salary" | "allowance";
  allowance_code?: string;
  amount: string;
  effective_from?: string;
}): Promise<BulkSalaryRaisePreview> {
  const res = await apiFetch("/api/employees/salary-raise/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function applySalaryRaise(body: {
  scope: "all" | "department" | "employees";
  department_code?: string;
  employee_ids?: string[];
  target: "contract_salary" | "probation_salary" | "allowance";
  allowance_code?: string;
  amount: string;
  effective_from?: string;
  confirm: boolean;
  confirm_again: boolean;
}): Promise<BulkSalaryRaiseResult> {
  const res = await apiFetch("/api/employees/salary-raise", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  cacheInvalidate("employees:");
  return res.json();
}

export type TransferTeamSkipped = {
  employee_code: string;
  full_name: string;
  reason: string;
};

export type TransferTeamPreview = {
  team_id: string;
  team_code: string;
  team_name: string;
  department_code: string | null;
  effective_from: string;
  total_selected: number;
  affected_count: number;
  skipped: TransferTeamSkipped[];
  message: string;
};

export type TransferTeamResult = TransferTeamPreview;

export type TransferTeamRequest = {
  employee_ids: string[];
  team_id: string;
  position_code?: string;
  effective_from: string;
  decision_no?: string;
  reason_code?: string;
  confirm?: boolean;
};

export async function previewTransferTeam(
  body: TransferTeamRequest,
): Promise<TransferTeamPreview> {
  const res = await apiFetch("/api/employees/transfer-team/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function applyTransferTeam(body: TransferTeamRequest): Promise<TransferTeamResult> {
  const res = await apiFetch("/api/employees/transfer-team", {
    method: "POST",
    body: JSON.stringify({ ...body, confirm: true }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type EmployeeAssignment = {
  id: string;
  employee_id: string;
  team_id: string;
  team_code: string | null;
  team_name: string | null;
  position_code: string | null;
  effective_from: string;
  effective_to: string | null;
  decision_no: string | null;
  reason_code: string | null;
  approved_by_name: string | null;
  created_at: string | null;
};

export async function fetchEmployeeAssignments(empId: string): Promise<EmployeeAssignment[]> {
  const res = await apiFetch(`/api/employees/${empId}/assignments`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function uploadEmployeePhoto(id: string, file: File): Promise<Employee> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiBase()}/api/employees/${id}/photo`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

/** Tải ảnh hồ sơ có Bearer → object URL (gọi revoke khi unmount). */
export type EmployeeViolation = {
  id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  occurred_at: string;
  title: string;
  description: string;
  penalty: string;
  has_attachment: boolean;
  attachment_url: string | null;
  created_at: string | null;
};

export type EmployeeViolationBoardItem = {
  employee_id: string;
  employee_code: string;
  full_name: string;
  department_code: string | null;
  status: string;
  violation_count: number;
  last_occurred_at: string | null;
};

export type EmployeeDocument = {
  id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  doc_type: string;
  title: string;
  note: string;
  file_url: string;
  created_at: string | null;
};

export async function fetchViolationBoard(): Promise<EmployeeViolationBoardItem[]> {
  const res = await apiFetch("/api/employees/violation-board");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type AnnualLeaveMonthDays = {
  jan: string;
  feb: string;
  mar: string;
  apr: string;
  may: string;
  jun: string;
  jul: string;
  aug: string;
  sep: string;
  oct: string;
  nov: string;
  dec: string;
};

export type AnnualLeaveGridRow = {
  employee_id: string | null;
  employee_code: string;
  full_name: string;
  department: string;
  team: string;
  join_date: string | null;
  al_days: string;
  used: string;
  unused: string;
  accrued_months: number;
  curr_al: string;
  curr_remaining: string;
  used_by_month: AnnualLeaveMonthDays;
};

export type AnnualLeaveGrid = {
  year: number | null;
  report_date: string | null;
  source_file: string | null;
  source_label: string;
  missing: boolean;
  notes: string[];
  employee_count: number;
  matched_in_db: number;
  accrued_through_month: number;
  employees: AnnualLeaveGridRow[];
};

export async function fetchAnnualLeaveGrid(): Promise<AnnualLeaveGrid> {
  const res = await apiFetch("/api/employees/annual-leave");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchEmployeeViolations(empId: string): Promise<EmployeeViolation[]> {
  const res = await apiFetch(`/api/employees/${empId}/violations`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchEmployeeDocuments(empId: string): Promise<EmployeeDocument[]> {
  const res = await apiFetch(`/api/employees/${empId}/documents`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createEmployeeDocument(
  empId: string,
  body: {
    title: string;
    doc_type?: string;
    note?: string;
    file: File;
  },
): Promise<EmployeeDocument> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("title", body.title);
  form.append("doc_type", body.doc_type ?? "other");
  form.append("note", body.note ?? "");
  form.append("file", body.file);
  const res = await fetch(`${getApiBase()}/api/employees/${empId}/documents`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteEmployeeDocument(empId: string, documentId: string): Promise<void> {
  const res = await apiFetch(`/api/employees/${empId}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readError(res));
}

export async function fetchDocumentFileObjectUrl(
  empId: string,
  documentId: string,
): Promise<string> {
  const token = getAccessToken();
  const res = await fetch(`${getApiBase()}/api/employees/${empId}/documents/${documentId}/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function createEmployeeViolation(
  empId: string,
  body: {
    occurred_at: string;
    title: string;
    description?: string;
    penalty?: string;
    file?: File | null;
  },
): Promise<EmployeeViolation> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("occurred_at", body.occurred_at);
  form.append("title", body.title);
  form.append("description", body.description ?? "");
  form.append("penalty", body.penalty ?? "");
  if (body.file) form.append("file", body.file);
  const res = await fetch(`${getApiBase()}/api/employees/${empId}/violations`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteEmployeeViolation(empId: string, violationId: string): Promise<void> {
  const res = await apiFetch(`/api/employees/${empId}/violations/${violationId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readError(res));
}

export async function fetchViolationAttachmentObjectUrl(
  empId: string,
  violationId: string,
): Promise<string> {
  const token = getAccessToken();
  const res = await fetch(
    `${getApiBase()}/api/employees/${empId}/violations/${violationId}/attachment`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function fetchEmployeePhotoObjectUrl(id: string): Promise<string | null> {
  const token = getAccessToken();
  const res = await fetch(`${getApiBase()}/api/employees/${id}/photo`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 404) return null;
  if (res.status === 401) {
    clearAuth();
    return null;
  }
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function downloadEmployeeImportTemplate(): Promise<void> {
  const res = await apiFetch("/api/employees/import-template");
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(cd);
  a.download = match ? match[1] : "mau-nhap-nhan-vien.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

export async function importEmployeesExcel(file: File): Promise<{
  created: number;
  updated: number;
  errors: string[];
  detail: string;
}> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(
    `${getApiBase()}/api/employees/import`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    },
  );
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as {
    created: number;
    updated: number;
    errors: string[];
    detail: string;
  };
  cacheInvalidate("employees:");
  return data;
}

export async function importAllowancesExcel(file: File): Promise<{
  created: number;
  updated: number;
  skipped_empty: number;
  errors: string[];
  detail: string;
}> {
  const token = getAccessToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(
    `${getApiBase()}/api/payroll/allowances/import`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    },
  );
  if (res.status === 401) clearAuth();
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as {
    created: number;
    updated: number;
    skipped_empty: number;
    errors: string[];
    detail: string;
  };
  cacheInvalidate("employees:");
  return data;
}

export type AllowanceAssignment = {
  id: string;
  employee_code: string;
  full_name: string;
  allowance_code: string;
  allowance_name: string;
  amount: string | number | null;
  include_in_si_base: boolean;
  include_in_ot_base: boolean;
};

export type AllowanceType = {
  code: string;
  name: string;
  include_in_si_base: boolean;
  include_in_ot_base: boolean;
  default_amount: string | number;
  proration: string;
};

export async function fetchAllowanceAssignments(
  employeeCode?: string,
): Promise<AllowanceAssignment[]> {
  const qs = employeeCode
    ? `?employee_code=${encodeURIComponent(employeeCode)}`
    : "";
  const res = await apiFetch(`/api/payroll/allowances${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchAllowanceTypes(opts?: {
  assignable?: boolean;
}): Promise<AllowanceType[]> {
  const qs = opts?.assignable ? "?assignable=true" : "";
  const res = await apiFetch(`/api/payroll/allowances/types${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function upsertAllowanceAssignment(body: {
  employee_code: string;
  allowance_code: string;
  amount: string;
}): Promise<AllowanceAssignment> {
  const res = await apiFetch("/api/payroll/allowances/assignments", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteAllowanceAssignment(id: string): Promise<void> {
  const res = await apiFetch(`/api/payroll/allowances/assignments/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readError(res));
}

export type SyncJob = {
  id: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  records_in: number;
  records_inserted: number;
  records_skipped: number;
  message: string;
  source: string;
  trigger: string;
  sync_date_from: string | null;
  sync_date_to: string | null;
};

export type IntegrationStatus = {
  agent_configured: boolean;
  last_job: SyncJob | null;
  last_success_at: string | null;
  punch_count: number;
  punch_unlinked_count: number;
  last_punch_at: string | null;
  stale_threshold_hours: number;
  hours_since_data: number | null;
  stale_warning: boolean;
  detail: string;
};

export type UnlinkedPunch = {
  id: number;
  employee_code: string;
  employee_id: string | null;
  punch_time: string;
  direction: string | null;
  sync_job_id: string | null;
  source: string;
  ma_cham_cong: string | null;
  device_id: string | null;
};

export async function fetchIntegrationStatus(): Promise<IntegrationStatus> {
  const res = await apiFetch("/api/integrations/status");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchSyncJobs(limit = 50): Promise<{ total: number; items: SyncJob[] }> {
  const res = await apiFetch(`/api/integrations/sync-jobs?limit=${limit}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function requestSyncNow(): Promise<SyncJob> {
  const res = await apiFetch("/api/attendance/sync-now", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function requestSyncRange(from: string, to: string): Promise<SyncJob> {
  const res = await apiFetch("/api/attendance/sync-range", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from, to }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchUnlinkedPunches(limit = 100): Promise<{
  total: number;
  items: UnlinkedPunch[];
}> {
  const res = await apiFetch(`/api/integrations/punches/unlinked?limit=${limit}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function relinkPunches(): Promise<{ updated: number; remaining_unlinked: number }> {
  const res = await apiFetch("/api/integrations/punches/relink", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type PayPeriod = {
  id: string;
  year: number;
  month: number;
  date_from: string;
  date_to: string;
  official_work_days: string | number;
  salary_divisor: string | number;
  status: string;
};

export type TimesheetMonth = {
  id: string;
  pay_period_id: string;
  period: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  worked_days: string | number;
  al_days: string | number;
  rem_days: string | number;
  late_count: number;
  early_count: number;
  ot_hours_weekday: string | number;
  ot_hours_external?: string | number;
  ot_hours_weekend: string | number;
  ot_hours_holiday: string | number;
};

export type LeaveType = {
  code: string;
  name: string;
  paid_by_company: boolean;
  counts_as_unauthorized: boolean;
  pay_ratio_percent: number | null;
  paid_by_si: boolean;
  affects_attendance_bonus: boolean;
  counts_as_worked_day: boolean;
  requires_document: boolean;
  max_days_per_year: number | null;
};

export type TimesheetAdjustment = {
  id: string;
  period: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  kind: string;
  leave_code: string | null;
  days: string | number | null;
  ot_type: string | null;
  ot_hours: string | number | null;
  note: string;
  created_by: string;
  created_at: string | null;
};

export type AttendanceDay = {
  id: string;
  employee_id?: string;
  employee_code: string;
  full_name: string;
  work_date: string;
  first_in?: string | null;
  last_out?: string | null;
  worked_hours?: string | number;
  late_minutes: number;
  early_minutes: number;
  ot_minutes: number;
  ot_on_books_minutes?: number;
  ot_external_minutes?: number;
  ot_type?: string | null;
  punch_count: number;
  is_workday?: boolean;
  sunday_hours?: string | number;
  holiday_hours?: string | number;
};

export async function fetchAttendanceDays(params: {
  from: string;
  to: string;
  employee_code?: string;
  anomalies_only?: boolean;
}): Promise<AttendanceDay[]> {
  const qs = new URLSearchParams({
    from: params.from,
    to: params.to,
  });
  if (params.employee_code) qs.set("employee_code", params.employee_code);
  if (params.anomalies_only) qs.set("anomalies_only", "true");
  const res = await apiFetch(`/api/attendance/days?${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchPayPeriod(period: string): Promise<PayPeriod> {
  const res = await apiFetch(`/api/attendance/pay-periods/${period}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchTimesheets(period: string): Promise<TimesheetMonth[]> {
  return cachedFetch(`timesheets:${period}`, async () => {
    const res = await apiFetch(`/api/attendance/timesheets?period=${encodeURIComponent(period)}`);
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  });
}

export async function rebuildTimesheets(period: string): Promise<{
  period: string;
  rows_upserted: number;
  message: string;
}> {
  const res = await apiFetch(
    `/api/attendance/timesheets/rebuild?period=${encodeURIComponent(period)}`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as {
    period: string;
    rows_upserted: number;
    message: string;
  };
  cacheInvalidate("timesheets:");
  return data;
}

/** Xuất Excel OT ngoài (ATM riêng) — tách khỏi bảng lương audit. */
export async function exportOtExternalExcel(period: string): Promise<Blob> {
  const res = await apiFetch(
    `/api/attendance/timesheets/${encodeURIComponent(period)}/export-ot-external`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.blob();
}

export type OtExternalPreviewRow = {
  employee_code: string;
  full_name: string;
  bank_account: string;
  raw_hours: number | string;
  effective_hours: number | string;
  ot_base: number | string;
  hourly_base: number | string;
  rate: number | string;
  amount_vnd: number | string;
};

export type OtExternalPreview = {
  period: string;
  employee_count: number;
  total_raw_hours: number | string;
  total_effective_hours: number | string;
  total_amount_vnd: number | string;
  policy_note: string;
  rows: OtExternalPreviewRow[];
};

export async function fetchOtExternalPreview(period: string): Promise<OtExternalPreview> {
  const res = await apiFetch(
    `/api/attendance/timesheets/${encodeURIComponent(period)}/ot-external-preview`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchLeaveTypes(): Promise<LeaveType[]> {
  const res = await apiFetch("/api/attendance/leave-types");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type LeaveRequestRow = {
  id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  team_code: string | null;
  department_code: string | null;
  team_name?: string | null;
  department_name?: string | null;
  leave_type_code: string;
  leave_type_name: string;
  from_date: string;
  to_date: string;
  from_half: boolean;
  to_half: boolean;
  total_days: string | number;
  reason: string;
  status: string;
  submitted_at: string | null;
  annual_leave_remaining: string | number | null;
  decided_note: string;
};

export async function fetchLeaveRequests(params?: {
  status?: string;
  employee_code?: string;
}): Promise<LeaveRequestRow[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.employee_code) qs.set("employee_code", params.employee_code);
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await apiFetch(`/api/attendance/leave-requests${suffix}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function bulkDecideLeaveRequests(body: {
  request_ids: string[];
  action: "approve" | "reject";
  decided_note?: string;
}): Promise<{
  approved_count: number;
  rejected_count: number;
  skipped: { id: string; employee_code: string | null; reason: string }[];
  message: string;
}> {
  const res = await apiFetch("/api/attendance/leave-requests/bulk-decide", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type AttendanceDayGridRow = AttendanceDay & {
  team_code: string | null;
  team_name: string | null;
  department_code: string | null;
  department_name: string | null;
  needs_action: boolean;
  row_flag: string;
  work_shift_id?: string | null;
  leave_code?: string | null;
  note?: string;
  sunday_hours?: string | number;
  holiday_hours?: string | number;
};

export async function fetchAttendanceDaysGrid(params: {
  date: string;
  needs_action_only?: boolean;
  department_id?: string;
}): Promise<AttendanceDayGridRow[]> {
  const qs = new URLSearchParams({ date: params.date });
  if (params.needs_action_only) qs.set("needs_action_only", "true");
  if (params.department_id) qs.set("department_id", params.department_id);
  const res = await apiFetch(`/api/attendance/days/grid?${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function patchAttendanceDayCell(body: {
  employee_code: string;
  work_date: string;
  first_in?: string | null;
  last_out?: string | null;
  leave_code?: string | null;
  note?: string | null;
  clear_note?: boolean;
  clear_times?: boolean;
  clear_first_in?: boolean;
  clear_last_out?: boolean;
}): Promise<AttendanceDay> {
  const res = await apiFetch("/api/attendance/days/cell", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  cacheInvalidate("timesheets:");
  return res.json();
}

export async function bulkPatchAttendanceDays(body: {
  work_date: string;
  employee_codes: string[];
  action: "set_leave" | "set_times" | "clear_note";
  leave_code?: string;
  first_in_time?: string;
  last_out_time?: string;
  note?: string;
  preview?: boolean;
}): Promise<{
  preview: boolean;
  affected_count: number;
  skipped: { employee_code: string | null; reason: string }[];
  message: string;
}> {
  const res = await apiFetch("/api/attendance/days/bulk", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  if (!body.preview) cacheInvalidate("timesheets:");
  return res.json();
}

export async function fetchAdjustments(period: string): Promise<TimesheetAdjustment[]> {
  const res = await apiFetch(`/api/attendance/adjustments?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createAdjustment(body: {
  period: string;
  employee_code: string;
  kind: string;
  leave_code?: string;
  days?: string;
  ot_type?: string;
  ot_hours?: string;
  note?: string;
}): Promise<TimesheetAdjustment> {
  const res = await apiFetch("/api/attendance/adjustments", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function deleteAdjustment(id: string): Promise<void> {
  const res = await apiFetch(`/api/attendance/adjustments/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
}

export async function fetchAttendanceAnomalies(
  dateFrom: string,
  dateTo: string,
): Promise<AttendanceDay[]> {
  const qs = new URLSearchParams({
    from: dateFrom,
    to: dateTo,
    anomalies_only: "true",
  });
  const res = await apiFetch(`/api/attendance/days?${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type AttendanceReviewIssue = {
  issue_type: string;
  severity: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  work_date: string | null;
  day_id: string | null;
  punch_count: number;
  message: string;
};

export type AttendanceReview = {
  period: string;
  date_from: string;
  date_to: string;
  period_status: string;
  issue_count: number;
  missing_punch: number;
  odd_punch: number;
  no_data: number;
  issues: AttendanceReviewIssue[];
  note: string;
};

export async function fetchAttendanceReview(period: string): Promise<AttendanceReview> {
  const res = await apiFetch(
    `/api/attendance/review?period=${encodeURIComponent(period)}`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function patchAttendanceDayManual(body: {
  employee_code: string;
  work_date: string;
  first_in: string;
  last_out: string;
  note?: string;
}): Promise<AttendanceDay> {
  const res = await apiFetch("/api/attendance/days/manual", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  cacheInvalidate("timesheets:");
  return res.json();
}

export type AiAlert = {
  id: string;
  rule_key: string;
  title: string;
  body: string;
  target_module: string;
  is_read: boolean;
  user_id: string | null;
  source_ref?: string | null;
  created_at: string | null;
};

export type AiAlertsMine = {
  unread_count: number;
  alerts: AiAlert[];
};

export async function fetchMyAlerts(unreadOnly = false): Promise<AiAlertsMine> {
  const qs = unreadOnly ? "?unread_only=true" : "";
  const res = await apiFetch(`/api/ai/alerts/mine${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function markAlertRead(id: string): Promise<AiAlert> {
  const res = await apiFetch(`/api/ai/alerts/${id}/read`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function markAllAlertsRead(): Promise<void> {
  const res = await apiFetch("/api/ai/alerts/read-all", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
}

export type DisputeTicket = {
  id: string;
  code: string;
  payslip_id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  period: string;
  reason_code: string;
  reason_label: string;
  description: string;
  status: string;
  payslip_status: string;
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  created_at: string | null;
  closed_at: string | null;
  hr_note: string | null;
  ai_summary: string | null;
};

export async function fetchDisputes(status?: string): Promise<DisputeTicket[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await apiFetch(`/api/disputes${qs}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function assignDispute(id: string, userId?: string): Promise<DisputeTicket> {
  const res = await apiFetch(`/api/disputes/${id}/assign`, {
    method: "POST",
    body: JSON.stringify(userId ? { user_id: userId } : {}),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function closeDispute(id: string, note = ""): Promise<DisputeTicket> {
  const res = await apiFetch(`/api/disputes/${id}/close`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type AiQueryResult = {
  answer: string;
  kind: string;
  job_id: string;
  dispute_id: string | null;
  dispute_code: string | null;
  model_name: string;
  tokens_in: number;
  tokens_out: number;
  stub: boolean;
  remaining_today: number;
  message: string;
};

export async function askAi(message: string, disputeId?: string): Promise<AiQueryResult> {
  const res = await apiFetch("/api/ai/query", {
    method: "POST",
    body: JSON.stringify({
      message,
      dispute_id: disputeId ?? null,
    }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type AiSettings = {
  enabled: boolean;
  model_name: string;
  max_queries_per_day: number;
  max_output_tokens: number;
  has_api_key: boolean;
  api_key_masked: string | null;
  source: string;
};

export async function fetchAiSettings(): Promise<AiSettings> {
  const res = await apiFetch("/api/ai/settings");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateAiSettings(body: {
  enabled?: boolean;
  model_name?: string;
  max_queries_per_day?: number;
  max_output_tokens?: number;
  api_key?: string;
  clear_api_key?: boolean;
}): Promise<AiSettings> {
  const res = await apiFetch("/api/ai/settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type MobilePunchSettings = {
  mode: "off" | "allowlist" | "all";
  department_codes: string[];
  extra_msnv: string[];
  gps_lat: number | null;
  gps_lng: number | null;
  gps_radius_m: number;
  require_photo: boolean;
  gps_enforced: boolean;
  persisted: boolean;
};

export async function fetchMobilePunchSettings(): Promise<MobilePunchSettings> {
  const res = await apiFetch("/api/config/mobile-punch");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateMobilePunchSettings(
  body: Partial<MobilePunchSettings> & { clear_gps?: boolean },
): Promise<MobilePunchSettings> {
  const res = await apiFetch("/api/config/mobile-punch", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type Payslip = {
  id: string;
  pay_period_id: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  pay_channel?: string | null;
  wd_salary: string | number;
  allowance_total: string | number;
  ot_pay: string | number;
  other_adjustments?: string | number;
  other_deductions?: string | number;
  gross: string | number;
  taxable_income?: string | number;
  bhxh: string | number;
  bhyt: string | number;
  bhtn: string | number;
  union_fee: string | number;
  pit_amount?: string | number;
  net: string | number;
  status: string;
  confirm_deadline?: string | null;
  worked_days?: string | number | null;
  al_days?: string | number | null;
  rem_days?: string | number | null;
  salary_divisor?: string | number | null;
  period?: string | null;
  prev_net?: string | number | null;
  net_delta?: string | number | null;
  lines?: Record<string, unknown> | null;
};

export type HRPayslipDetail = {
  payslip: Payslip;
  period: string;
  work_lines: PayslipComponentLine[];
  allowance_lines: PayslipComponentLine[];
  deduction_lines: PayslipComponentLine[];
  annual_leave_remaining?: string | number | null;
};

export type PayslipComponentLine = {
  id: string;
  payslip_id: string;
  component_code: string;
  component_name: string;
  segment: string;
  seq_no: number;
  quantity?: string | number | null;
  unit?: string | null;
  unit_amount?: string | number | null;
  amount: string | number;
  note?: string | null;
  sort_order: number;
  kind: string;
};

export type PayPeriodStatus = {
  id: string;
  period: string;
  year: number;
  month: number;
  official_work_days: string | number;
  salary_divisor: string | number;
  status: string;
};

export type PeriodActionResult = {
  period: PayPeriodStatus;
  affected_payslips: number;
  message: string;
};

export type PayrollCalculateResult = {
  run: {
    id: string;
    status: string;
    employee_count: number;
    message: string;
  };
  payslips: Payslip[];
  message: string;
};

export type PolicyOption = {
  id: string;
  name: string;
  effective_from: string;
  is_active: boolean;
};

export type PayslipAmounts = {
  wd_salary: string | number;
  allowance_total: string | number;
  ot_pay: string | number;
  gross: string | number;
  pit_amount: string | number;
  net: string | number;
  bonus_total: string | number;
};

export type SimulateRow = {
  employee_id: string;
  employee_code: string;
  full_name: string;
  current: PayslipAmounts | null;
  simulated: PayslipAmounts;
  delta_net: string | number;
};

export type SimulateResult = {
  period: string;
  policy_package_id: string | null;
  policy_package_name: string;
  employee_count: number;
  rows: SimulateRow[];
  message: string;
};

export async function fetchSimulatePolicyOptions(): Promise<PolicyOption[]> {
  const res = await apiFetch("/api/payroll/simulate/policy-options");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function runPayrollSimulate(body: {
  period: string;
  policy_package_id?: string | null;
  scope?: string;
  department_id?: string | null;
  team_id?: string | null;
  employee_codes?: string[];
}): Promise<SimulateResult> {
  const res = await apiFetch("/api/payroll/simulate", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function calculatePayroll(period: string): Promise<PayrollCalculateResult> {
  const res = await apiFetch(`/api/payroll/periods/${encodeURIComponent(period)}/calculate`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as PayrollCalculateResult;
  cacheInvalidate("payslips:");
  cacheInvalidate("timesheets:");
  return data;
}

export async function fetchPayslips(period: string): Promise<Payslip[]> {
  return cachedFetch(`payslips:${period}`, async () => {
    const res = await apiFetch(`/api/payroll/payslips?period=${encodeURIComponent(period)}`);
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  });
}

export async function fetchHRPayslipDetail(payslipId: string): Promise<HRPayslipDetail> {
  const res = await apiFetch(`/api/payroll/payslips/${encodeURIComponent(payslipId)}/detail`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchPayrollPeriod(period: string): Promise<PayPeriodStatus | null> {
  const res = await apiFetch(`/api/payroll/periods/${encodeURIComponent(period)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function publishPayroll(period: string): Promise<PeriodActionResult> {
  const res = await apiFetch(`/api/payroll/periods/${encodeURIComponent(period)}/publish`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as PeriodActionResult;
  cacheInvalidate("payslips:");
  return data;
}

export type PayslipAdjustment = {
  id: string;
  period: string;
  employee_id: string;
  employee_code: string;
  full_name: string;
  kind: string;
  reason: string;
  amount: string | number;
  created_by: string;
  created_at: string | null;
};

export async function fetchPayAdjustments(period: string): Promise<PayslipAdjustment[]> {
  const res = await apiFetch(
    `/api/payroll/adjustments?period=${encodeURIComponent(period)}`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function createPayAdjustment(body: {
  period: string;
  employee_code: string;
  kind: string;
  reason: string;
  amount: string | number;
}): Promise<PayslipAdjustment> {
  const res = await apiFetch("/api/payroll/adjustments", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await readError(res));
  const row = (await res.json()) as PayslipAdjustment;
  cacheInvalidate("payslips:");
  return row;
}

export async function deletePayAdjustment(id: string): Promise<void> {
  const res = await apiFetch(`/api/payroll/adjustments/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res));
  cacheInvalidate("payslips:");
}

export async function lockPayroll(period: string): Promise<PeriodActionResult> {
  const res = await apiFetch(`/api/payroll/periods/${encodeURIComponent(period)}/lock`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as PeriodActionResult;
  cacheInvalidate("payslips:");
  return data;
}

export async function unlockPayroll(period: string): Promise<PeriodActionResult> {
  const res = await apiFetch(`/api/payroll/periods/${encodeURIComponent(period)}/unlock`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as PeriodActionResult;
  cacheInvalidate("payslips:");
  return data;
}

export async function reopenPayroll(period: string): Promise<PeriodActionResult> {
  const res = await apiFetch(`/api/payroll/periods/${encodeURIComponent(period)}/reopen`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res));
  const data = (await res.json()) as PeriodActionResult;
  cacheInvalidate("payslips:");
  return data;
}

export async function downloadPayrollExport(
  period: string,
  channel: "ATM" | "CASH" | "ALL" = "ALL",
  filters: { departmentId?: string; employeeCode?: string } = {},
): Promise<void> {
  const qs = new URLSearchParams({ channel });
  if (filters.departmentId) qs.set("department_id", filters.departmentId);
  if (filters.employeeCode) qs.set("employee_code", filters.employeeCode);
  const res = await apiFetch(
    `/api/payroll/periods/${encodeURIComponent(period)}/export?${qs.toString()}`,
  );
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(cd);
  a.download = match ? match[1] : `luong_${period}_${channel.toLowerCase()}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

export type DeptKpiRow = {
  department_code: string;
  department_name: string;
  category: string;
  headcount: number;
  worked_days: string | number;
  ot_hours: string | number;
  ot_pay: string | number;
};

export type KpiPeriod = {
  period: string;
  official_work_days: string | number;
  param_b3: string | number;
  headcount: number;
  begin_hc: number;
  recruit: number;
  resign: number;
  end_hc: number;
  attendants: string | number;
  monthly_manpower: string | number;
  attendance_rate_pct: string | number | null;
  ot_hours: string | number;
  reference_hours: string | number;
  ot_rate_pct: string | number | null;
  ot_pay_total: string | number;
  turnover_rate_pct: string | number | null;
  open_disputes: number;
  by_category: {
    category: string;
    label: string;
    headcount: number;
    worked_days: string | number;
    ot_hours: string | number;
  }[];
  by_department: DeptKpiRow[];
  formula_note: string;
};

export type OverviewData = {
  period: string;
  total_employees: number;
  attendance_rate_pct: string | number | null;
  ot_pay_total: string | number;
  open_disputes: number;
  ot_hours: string | number;
  turnover_rate_pct: string | number | null;
  recent_alerts: {
    id: string;
    title: string;
    body: string;
    target_module: string;
    is_read: boolean;
  }[];
  by_department: DeptKpiRow[];
};

export async function fetchKpi(period: string): Promise<KpiPeriod> {
  const res = await apiFetch(`/api/reports/kpi?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchOverview(period: string): Promise<OverviewData> {
  const res = await apiFetch(`/api/reports/overview?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function downloadKpiExport(period: string): Promise<void> {
  const res = await apiFetch(`/api/reports/kpi/export?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error(await readError(res));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `kpi_${period}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

export type BlackBox = {
  actions: {
    id: string;
    actor_username: string | null;
    action: string;
    entity_type: string;
    entity_id: string | null;
    summary: string;
    created_at: string | null;
  }[];
  exports: {
    id: string;
    username: string | null;
    full_name: string | null;
    kind: string;
    period: string | null;
    row_count: number;
    filename: string;
    created_at: string | null;
  }[];
  policy_confirms: {
    id: string;
    package_id: string;
    actor_username: string | null;
    confirm_step: number;
    note: string;
    created_at: string | null;
  }[];
  note: string;
};

export async function fetchBlackBox(limit = 80): Promise<BlackBox> {
  const res = await apiFetch(`/api/audit/blackbox?limit=${limit}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export type InsuranceSummary = {
  period: string;
  employee_count: number;
  total_bhxh: string | number;
  total_bhyt: string | number;
  total_bhtn: string | number;
  total_union_fee: string | number;
  total_pit: string | number;
  total_gross: string | number;
  total_net: string | number;
  pit_enabled_in_snapshot: boolean | null;
};

export type InsuranceRow = {
  employee_id: string;
  employee_code: string;
  full_name: string;
  si_enrolled: boolean;
  pit_enrolled: boolean;
  tax_dependent_count: number;
  si_base: string | number;
  gross: string | number;
  bhxh: string | number;
  bhyt: string | number;
  bhtn: string | number;
  union_fee: string | number;
  pit_amount: string | number;
  net: string | number;
};

export async function fetchInsuranceSummary(period: string): Promise<InsuranceSummary> {
  const res = await apiFetch(
    `/api/insurance/periods/${encodeURIComponent(period)}/summary`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchInsuranceRows(period: string): Promise<InsuranceRow[]> {
  const res = await apiFetch(
    `/api/insurance/periods/${encodeURIComponent(period)}/rows`,
  );
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}
