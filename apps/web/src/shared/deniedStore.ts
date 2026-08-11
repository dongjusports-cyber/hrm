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

export function showDenied(fullName: string) {
  state = {
    open: true,
    message: `Trợ Lý AI xin chào ${fullName}, bạn không có quyền truy cập.\nVui lòng liên hệ Admin.`,
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
