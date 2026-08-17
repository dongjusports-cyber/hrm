import { useSyncExternalStore } from "react";

export type WorkerUser = {
  id: string;
  employee_code: string;
  full_name: string;
  must_change_password: boolean;
  employee_id: string | null;
  department_code?: string | null;
  can_mobile_punch?: boolean;
  punch_blocked_reason?: string | null;
  gps_required?: boolean;
};

type State = {
  accessToken: string | null;
  refreshToken: string | null;
  worker: WorkerUser | null;
};

const KEY = "djhrm_worker_auth";

function load(): State {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { accessToken: null, refreshToken: null, worker: null };
    return JSON.parse(raw) as State;
  } catch {
    return { accessToken: null, refreshToken: null, worker: null };
  }
}

let state: State = load();
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function persist() {
  if (state.accessToken) localStorage.setItem(KEY, JSON.stringify(state));
  else localStorage.removeItem(KEY);
  emit();
}

export function setWorkerAuth(payload: {
  access_token: string;
  refresh_token: string;
  worker: WorkerUser;
}) {
  state = {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    worker: payload.worker,
  };
  persist();
}

export function clearWorkerAuth() {
  state = { accessToken: null, refreshToken: null, worker: null };
  persist();
}

export function patchWorkerUser(patch: Partial<WorkerUser>) {
  if (!state.worker) return;
  state = { ...state, worker: { ...state.worker, ...patch } };
  persist();
}

export function getWorkerToken() {
  return state.accessToken;
}

export function useWorkerAuth() {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}
