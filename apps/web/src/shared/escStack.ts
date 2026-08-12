/** Ngăn xếp ESC — tầng trên cùng đóng trước, hết tầng mới fallback (Portal / hub). */

type EscHandler = () => void;

const stack: EscHandler[] = [];
let fallback: (() => void) | null = null;
let rootInstalled = false;

function ensureRoot() {
  if (rootInstalled) return;
  rootInstalled = true;
  window.addEventListener(
    "keydown",
    (e) => {
      if (e.key !== "Escape") return;
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
