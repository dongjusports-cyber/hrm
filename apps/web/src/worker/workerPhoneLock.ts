export type WorkerPhoneLock = {
  employee_code: string;
  full_name: string;
};

const KEY = "djhrm_worker_phone_lock";

export function getWorkerPhoneLock(): WorkerPhoneLock | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WorkerPhoneLock;
    const code = String(parsed.employee_code ?? "").trim();
    if (!code) return null;
    return { employee_code: code, full_name: String(parsed.full_name ?? "").trim() };
  } catch {
    return null;
  }
}

export function setWorkerPhoneLock(lock: WorkerPhoneLock): void {
  const employee_code = lock.employee_code.trim();
  if (!employee_code) return;
  localStorage.setItem(
    KEY,
    JSON.stringify({ employee_code, full_name: lock.full_name.trim() }),
  );
}

export function rememberWorkerPhoneLock(worker: { employee_code?: string; full_name?: string } | null | undefined): void {
  const code = String(worker?.employee_code ?? "").trim();
  if (!code) return;
  setWorkerPhoneLock({ employee_code: code, full_name: String(worker?.full_name ?? "").trim() });
}

export function phoneLockBlocksOtherMsnv(typedCode: string, lock: WorkerPhoneLock | null): boolean {
  if (!lock) return false;
  return typedCode.trim() !== lock.employee_code;
}
