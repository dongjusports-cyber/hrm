import { useSyncExternalStore } from "react";

export type AuthUser = {
  id: string;
  username: string;
  full_name: string;
  role: string;
  is_active?: boolean;
  must_change_password: boolean;
  modules: string[];
  permissions: string[];
};

type AuthState = {
  accessToken: string | null;
  user: AuthUser | null;
};

const STORAGE_KEY = "djhrm_auth";

function empty(): AuthState {
  return { accessToken: null, user: null };
}

function load(): AuthState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return empty();
    const parsed = JSON.parse(raw) as AuthState & { refreshToken?: unknown };
    const next: AuthState = {
      accessToken: parsed.accessToken ?? null,
      user: parsed.user ?? null,
    };
    if ("refreshToken" in parsed) {
      if (next.accessToken) localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      else localStorage.removeItem(STORAGE_KEY);
    }
    return next;
  } catch {
    return empty();
  }
}

let state: AuthState = load();
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function persist() {
  if (state.accessToken) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
  emit();
}

export function setAuth(payload: {
  access_token: string;
  user: AuthUser;
}) {
  state = {
    accessToken: payload.access_token,
    user: payload.user,
  };
  persist();
}

export function clearAuth() {
  state = empty();
  persist();
  void import("./clientCache").then((m) => m.cacheClearAll());
  void import("./keepAlive").then((m) => m.resetKeepAlive());
}

export function patchAuthUser(patch: Partial<AuthUser>) {
  if (!state.user) return;
  state = { ...state, user: { ...state.user, ...patch } };
  persist();
}

export function getAccessToken() {
  return state.accessToken;
}

export function useAuth() {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
}
