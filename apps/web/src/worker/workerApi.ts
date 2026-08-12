import { getApiBase } from "../shared/apiBase";
import { clearWorkerAuth, getWorkerToken, setWorkerAuth, type WorkerUser } from "./workerAuthStore";

async function readError(res: Response): Promise<string> {
  const data = await res.json().catch(() => ({}));
  return (data as { detail?: string }).detail ?? "Trợ Lý AI: thao tác thất bại.";
}

async function workerFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getWorkerToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${getApiBase()}${path}`, { ...init, headers });
  if (res.status === 401) clearWorkerAuth();
  return res;
}

export async function workerLogin(employee_code: string, password: string): Promise<WorkerUser> {
  let res: Response;
  try {
    res = await fetch(`${getApiBase()}/api/worker/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ employee_code, password }),
    });
  } catch {
    const host =
      typeof window !== "undefined" ? window.location.hostname : "192.168.x.x";
    throw new Error(
      `Không kết nối được máy chủ. Điện thoại phải cùng WiFi với máy HR, mở http://${host}:5173/worker/login ` +
        `(không dùng localhost). Nếu vẫn lỗi: chạy ops/open-firewall-mobile.ps1 (Admin) trên máy tính.`,
    );
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string }).detail ?? "Đăng nhập thất bại.");
  setWorkerAuth(data as { access_token: string; refresh_token: string; worker: WorkerUser });
  return (data as { worker: WorkerUser }).worker;
}

export type WorkerPayslipListItem = {
  id: string;
  period: string;
  status: string;
  net: string | number;
  gross: string | number;
  confirm_deadline: string | null;
};

export type MoneyLine = { label: string; amount: string | number };

export type WorkerPayslipDetail = {
  id: string;
  period: string;
  status: string;
  employee_code: string;
  full_name: string;
  net: string | number;
  gross: string | number;
  wd_salary: string | number;
  allowance_total: string | number;
  ot_pay: string | number;
  worked_days: string | number | null;
  al_days: string | number | null;
  rem_days: string | number | null;
  confirm_deadline: string | null;
  confirmed_at: string | null;
  income_lines: MoneyLine[];
  deduction_lines: MoneyLine[];
  can_confirm: boolean;
  can_dispute: boolean;
  message: string;
};

export type DisputeReason = { code: string; label: string };

export type WorkerDisputeTicket = {
  id: string;
  code: string;
  period: string;
  reason_code: string;
  reason_label: string;
  description: string;
  status: string;
};

export async function fetchWorkerPayslips(): Promise<WorkerPayslipListItem[]> {
  const res = await workerFetch("/api/worker/payslips");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchWorkerPayslip(id: string): Promise<WorkerPayslipDetail> {
  const res = await workerFetch(`/api/worker/payslips/${id}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function confirmWorkerPayslip(id: string): Promise<WorkerPayslipDetail> {
  const res = await workerFetch(`/api/worker/payslips/${id}/confirm`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchDisputeReasons(): Promise<DisputeReason[]> {
  const res = await workerFetch("/api/worker/dispute-reasons");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function disputeWorkerPayslip(
  id: string,
  reason_code: string,
  description: string,
): Promise<WorkerDisputeTicket> {
  const res = await workerFetch(`/api/worker/payslips/${id}/dispute`, {
    method: "POST",
    body: JSON.stringify({ reason_code, description }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function workerChangePassword(
  current_password: string,
  new_password: string,
): Promise<string> {
  const res = await workerFetch("/api/worker/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string }).detail ?? "Đổi mật khẩu thất bại.");
  return (data as { detail: string }).detail;
}

export type WorkerLeaveType = {
  code: string;
  name: string;
};

export type WorkerLeaveRequest = {
  id: string;
  leave_type_code: string;
  leave_type_name: string;
  from_date: string;
  to_date: string;
  total_days: string | number;
  reason: string;
  status: string;
  annual_leave_remaining: string | number | null;
};

export async function fetchWorkerLeaveTypes(): Promise<WorkerLeaveType[]> {
  const res = await workerFetch("/api/worker/leave-types");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchWorkerLeaveRequests(): Promise<WorkerLeaveRequest[]> {
  const res = await workerFetch("/api/worker/leave-requests");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function submitWorkerLeaveRequest(body: {
  leave_type_code: string;
  from_date: string;
  to_date: string;
  reason?: string;
  submit?: boolean;
}): Promise<WorkerLeaveRequest> {
  const res = await workerFetch("/api/worker/leave-requests", {
    method: "POST",
    body: JSON.stringify({ ...body, submit: body.submit ?? true }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}
