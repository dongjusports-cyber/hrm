/** Trạng thái form hồ sơ NV — dùng chung create (9 trường) và sửa (6 tab). */

export type ProfileTab =
  | "all"
  | "personal"
  | "address"
  | "insurance"
  | "work"
  | "salary"
  | "experience";

export type EmpExtraTab = "violations" | "documents";

export type EmpTab = ProfileTab | EmpExtraTab;

export const PROFILE_TABS: { id: ProfileTab; label: string }[] = [
  { id: "all", label: "Tổng hợp" },
  { id: "personal", label: "Cá nhân" },
  { id: "address", label: "Cư trú & giấy tờ" },
  { id: "insurance", label: "Bảo hiểm" },
  { id: "work", label: "Công việc" },
  { id: "salary", label: "Lương & phụ cấp" },
  { id: "experience", label: "Kinh nghiệm" },
];

export type EmployeeFormState = {
  employee_code: string;
  full_name: string;
  department_code: string;
  team_id: string;
  position_title: string;
  contract_salary: string;
  probation_salary: string;
  pay_channel: string;
  status: string;
  join_date: string;
  resign_date: string;
  contract_signed_at: string;
  gender: string;
  birth_date: string;
  birth_place_code: string;
  nationality_code: string;
  ethnicity_code: string;
  religion_code: string;
  marital_status: string;
  children_count: string;
  education_code: string;
  id_number: string;
  id_issue_date: string;
  id_issue_place_code: string;
  permanent_address: string;
  temporary_address: string;
  urgent_contact: string;
  si_book_no: string;
  phone: string;
  bank_account: string;
  si_base_override: string;
  si_enrolled: boolean;
  pit_enrolled: boolean;
  tax_dependent_count: string;
  union_fee_override: string;
};

export const emptyEmployeeForm: EmployeeFormState = {
  employee_code: "",
  full_name: "",
  department_code: "",
  team_id: "",
  position_title: "",
  contract_salary: "0",
  probation_salary: "0",
  pay_channel: "ATM",
  status: "active",
  join_date: "",
  resign_date: "",
  contract_signed_at: "",
  gender: "",
  birth_date: "",
  birth_place_code: "",
  nationality_code: "",
  ethnicity_code: "",
  religion_code: "",
  marital_status: "",
  children_count: "0",
  education_code: "",
  id_number: "",
  id_issue_date: "",
  id_issue_place_code: "",
  permanent_address: "",
  temporary_address: "",
  urgent_contact: "",
  si_book_no: "",
  phone: "",
  bank_account: "",
  si_base_override: "",
  si_enrolled: true,
  pit_enrolled: true,
  tax_dependent_count: "0",
  union_fee_override: "",
};

export function parseEmpTab(raw: string | null, isNew: boolean): EmpTab {
  if (isNew) return "work";
  const ok: EmpTab[] = [
    "all",
    "personal",
    "address",
    "insurance",
    "work",
    "salary",
    "experience",
    "violations",
    "documents",
  ];
  if (raw && ok.includes(raw as EmpTab)) return raw as EmpTab;
  return "all";
}

export function employeeToForm(e: {
  employee_code: string;
  full_name: string;
  department_code?: string | null;
  team_id?: string | null;
  position_title?: string | null;
  contract_salary?: string | number;
  probation_salary?: string | number;
  pay_channel?: string | null;
  status?: string | null;
  join_date?: string | null;
  resign_date?: string | null;
  contract_signed_at?: string | null;
  gender?: string | null;
  birth_date?: string | null;
  birth_place_code?: string | null;
  nationality_code?: string | null;
  ethnicity_code?: string | null;
  religion_code?: string | null;
  marital_status?: string | null;
  children_count?: number | null;
  education_code?: string | null;
  id_number?: string | null;
  id_issue_date?: string | null;
  id_issue_place_code?: string | null;
  permanent_address?: string | null;
  temporary_address?: string | null;
  urgent_contact?: string | null;
  si_book_no?: string | null;
  phone?: string | null;
  bank_account?: string | null;
  si_base_override?: string | number | null;
  si_enrolled?: boolean;
  pit_enrolled?: boolean;
  tax_dependent_count?: number | null;
  union_fee_override?: string | number | null;
}, toDateInput: (v: string | null | undefined) => string): EmployeeFormState {
  return {
    employee_code: e.employee_code,
    full_name: e.full_name,
    department_code: e.department_code ?? "",
    team_id: e.team_id ?? "",
    position_title: e.position_title ?? "",
    contract_salary: String(e.contract_salary ?? "0"),
    probation_salary: String(e.probation_salary ?? "0"),
    pay_channel: e.pay_channel || "ATM",
    status: e.status || "active",
    join_date: toDateInput(e.join_date),
    resign_date: toDateInput(e.resign_date),
    contract_signed_at: toDateInput(e.contract_signed_at),
    gender: e.gender ?? "",
    birth_date: toDateInput(e.birth_date),
    birth_place_code: e.birth_place_code ?? "",
    nationality_code: e.nationality_code ?? "",
    ethnicity_code: e.ethnicity_code ?? "",
    religion_code: e.religion_code ?? "",
    marital_status: e.marital_status ?? "",
    children_count: String(e.children_count ?? 0),
    education_code: e.education_code ?? "",
    id_number: e.id_number ?? "",
    id_issue_date: toDateInput(e.id_issue_date),
    id_issue_place_code: e.id_issue_place_code ?? "",
    permanent_address: e.permanent_address ?? "",
    temporary_address: e.temporary_address ?? "",
    urgent_contact: e.urgent_contact ?? "",
    si_book_no: e.si_book_no ?? "",
    phone: e.phone ?? "",
    bank_account: e.bank_account ?? "",
    si_base_override: e.si_base_override != null ? String(e.si_base_override) : "",
    si_enrolled: e.si_enrolled !== false,
    pit_enrolled: e.pit_enrolled !== false,
    tax_dependent_count: String(e.tax_dependent_count ?? 0),
    union_fee_override: e.union_fee_override != null ? String(e.union_fee_override) : "",
  };
}

export function formToPayload(form: EmployeeFormState, isNew: boolean) {
  const base = {
    full_name: form.full_name,
    team_id: form.team_id || undefined,
    position_title: form.position_title || undefined,
    contract_salary: form.contract_salary,
    probation_salary: form.probation_salary,
    pay_channel: form.pay_channel,
    status: form.status,
    join_date: form.join_date || null,
  };
  if (isNew) return base;
  return {
    ...base,
    resign_date: form.resign_date || null,
    contract_signed_at: form.contract_signed_at || null,
    gender: form.gender || null,
    birth_date: form.birth_date || null,
    birth_place_code: form.birth_place_code || null,
    nationality_code: form.nationality_code || null,
    ethnicity_code: form.ethnicity_code || null,
    religion_code: form.religion_code || null,
    marital_status: form.marital_status || null,
    children_count: Number(form.children_count || 0),
    education_code: form.education_code || null,
    id_number: form.id_number || null,
    id_issue_date: form.id_issue_date || null,
    id_issue_place_code: form.id_issue_place_code || null,
    permanent_address: form.permanent_address || null,
    temporary_address: form.temporary_address || null,
    urgent_contact: form.urgent_contact || null,
    si_book_no: form.si_book_no || null,
    phone: form.phone || null,
    bank_account: form.bank_account || null,
    si_base_override: form.si_base_override.trim() ? form.si_base_override : null,
    si_enrolled: form.si_enrolled,
    pit_enrolled: form.pit_enrolled,
    // tax_dependent_count — tính từ thân nhân, không gửi khi lưu (5.3)
    union_fee_override: form.union_fee_override.trim() ? form.union_fee_override : null,
  };
}
