import { useSyncExternalStore } from "react";

type State = {
  open: boolean;
  message: string;
};

let state: State = { open: false, message: "" };
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export const DENIED_MESSAGE = "Bạn không có quyền truy cập, vui lòng liên hệ Admin.";

export function showDenied(_fullName?: string) {
  state = {
    open: true,
    message: DENIED_MESSAGE,
  };
  emit();
}

export function closeDenied() {
  state = { ...state, open: false };
  emit();
}

export function useDeniedStore() {
  const snap = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
  return { ...snap, close: closeDenied };
}
