/**
 * @locked Ngăn xếp ESC — KHÔNG sửa tùy tiện. Xem `.cursor/rules/esc-keyboard.mdc`
 * Chạy: `npm test -- escKeyboard`
 *
 * Thứ tự: (1) hoàn tác ô nhập (2) AG Grid tự hủy nếu còn editor (3) overlay stack (4) quay trang.
 */

import {
  installGlobalFieldEsc,
  isEditableFormField,
  registerActiveFieldEsc,
  tryRevertActiveFieldEsc,
} from "./formFieldEsc";

type EscHandler = () => void;

const stack: EscHandler[] = [];
let fallback: (() => void) | null = null;
let rootInstalled = false;

/** AG Grid đang sửa ô — để ESC hủy edit như Excel, không chặn. */
export function isGridCellEditing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return !!target.closest(".ag-cell-inline-editing, .ag-popup-editor");
}

/** Ô nhập đang focus nhưng chưa kịp đăng ký snapshot (race focusin). */
function tryRevertFocusedFieldEsc(): boolean {
  const active = document.activeElement;
  if (!isEditableFormField(active)) return false;
  registerActiveFieldEsc(active);
  return tryRevertActiveFieldEsc();
}

function ensureRoot() {
  if (rootInstalled) return;
  rootInstalled = true;
  installGlobalFieldEsc();
  window.addEventListener(
    "keydown",
    (e) => {
      if (e.key !== "Escape") return;

      if (tryRevertActiveFieldEsc() || tryRevertFocusedFieldEsc()) {
        e.preventDefault();
        e.stopImmediatePropagation();
        return;
      }

      if (isGridCellEditing(e.target)) {
        return;
      }

      if (stack.length === 0) {
        if (!fallback) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        fallback();
        return;
      }

      e.preventDefault();
      e.stopImmediatePropagation();
      stack[stack.length - 1]();
    },
    true,
  );
}

export function registerEscHandler(handler: EscHandler): () => void {
  ensureRoot();
  stack.push(handler);
  return () => {
    const i = stack.lastIndexOf(handler);
    if (i >= 0) stack.splice(i, 1);
  };
}

export function setEscFallback(fn: (() => void) | null) {
  fallback = fn;
}

export function escStackDepth(): number {
  return stack.length;
}
