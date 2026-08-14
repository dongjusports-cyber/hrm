/**
 * @locked ESC trong ô nhập — KHÔNG sửa tùy tiện. Xem `.cursor/rules/esc-keyboard.mdc`
 */
import { type RefObject, useEffect, useRef } from "react";
import { useEscLayer } from "./useEscLayer";

export function isEditableFormField(
  target: EventTarget | null,
): target is HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement {
  if (!(target instanceof HTMLElement)) return false;
  if (target instanceof HTMLInputElement) {
    const type = (target.type || "text").toLowerCase();
    if (["button", "submit", "reset", "checkbox", "radio", "file", "hidden", "image"].includes(type)) {
      return false;
    }
    return !target.readOnly && !target.disabled;
  }
  if (target instanceof HTMLTextAreaElement) return !target.readOnly && !target.disabled;
  if (target instanceof HTMLSelectElement) return !target.disabled;
  return false;
}

function getFieldValue(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): string {
  return el.value;
}

/** Gán lại giá trị controlled input (React) rồi bắn input/change. */
export function setFormFieldValue(
  el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  value: string,
) {
  if (el instanceof HTMLSelectElement) {
    el.value = value;
  } else {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
    descriptor?.set?.call(el, value);
  }
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

type ActiveFieldEsc = {
  el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
  value: string;
  onRevert?: () => void;
};

let activeFieldEsc: ActiveFieldEsc | null = null;
let globalFieldListenerInstalled = false;

export function registerActiveFieldEsc(
  el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  onRevert?: () => void,
) {
  activeFieldEsc = { el, value: getFieldValue(el), onRevert };
}

function ensureGlobalFieldEsc() {
  if (globalFieldListenerInstalled) return;
  if (typeof document === "undefined") return;
  globalFieldListenerInstalled = true;
  document.addEventListener("focusin", (e) => {
    if (!isEditableFormField(e.target)) {
      clearActiveFieldEsc();
      return;
    }
    registerActiveFieldEsc(e.target);
  });
  document.addEventListener("focusout", (e) => {
    const related = e.relatedTarget as Node | null;
    if (related && isEditableFormField(related)) return;
    clearActiveFieldEsc(e.target instanceof HTMLElement ? e.target : undefined);
  });
}

/** Gọi từ escStack khi khởi tạo listener ESC (tránh chạy lúc import trong Node test). */
export function installGlobalFieldEsc() {
  ensureGlobalFieldEsc();
}

export function clearActiveFieldEsc(el?: HTMLElement) {
  if (!activeFieldEsc) return;
  if (!el || activeFieldEsc.el === el) activeFieldEsc = null;
}

/** Gọi từ escStack — hoàn tác ô đang focus (Excel-like). */
export function tryRevertActiveFieldEsc(): boolean {
  if (!activeFieldEsc) return false;
  const { el, value } = activeFieldEsc;
  if (document.activeElement !== el) return false;
  setFormFieldValue(el, value);
  activeFieldEsc.onRevert?.();
  el.blur();
  activeFieldEsc = null;
  return true;
}

export function isFieldFocusedInRoot(root: HTMLElement | null): boolean {
  if (!root) return false;
  const active = document.activeElement;
  return isEditableFormField(active) && root.contains(active);
}

type SheetKeyboardOptions = {
  open: boolean;
  containerRef: RefObject<HTMLElement | null>;
  /** ESC khi không đang sửa ô — quay tab trước. Trả true nếu đã xử lý. */
  onTabBack?: () => boolean;
  /** ESC khi `onTabBack` không xử lý — đóng sheet / quay trang trước (≈ nút Đóng). */
  onClose?: () => void;
};

/**
 * ESC trong ô nhập: hoàn tác về giá trị lúc focus, blur khỏi ô (escStack xử lý).
 * Enter trong ô (trừ textarea): blur = commit qua onBlur/onChange.
 * ESC ngoài ô: `onTabBack` trước, rồi `onClose`.
 */
export function useSheetKeyboard({ open, containerRef, onTabBack, onClose }: SheetKeyboardOptions) {
  const onTabBackRef = useRef(onTabBack);
  onTabBackRef.current = onTabBack;
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) {
      clearActiveFieldEsc();
      return;
    }
    const root = containerRef.current;
    if (!root) return;

    function onFocusIn(e: FocusEvent) {
      if (!isEditableFormField(e.target)) {
        clearActiveFieldEsc();
        return;
      }
      registerActiveFieldEsc(e.target);
    }

    function onFocusOut(e: FocusEvent) {
      const related = e.relatedTarget as Node | null;
      if (root && related && root.contains(related) && isEditableFormField(related)) return;
      clearActiveFieldEsc(e.target instanceof HTMLElement ? e.target : undefined);
    }

    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "Enter") return;
      if (!isEditableFormField(e.target)) return;
      if (e.target instanceof HTMLTextAreaElement) return;
      e.preventDefault();
      e.stopPropagation();
      (e.target as HTMLElement).blur();
    }

    root.addEventListener("focusin", onFocusIn);
    root.addEventListener("focusout", onFocusOut);
    root.addEventListener("keydown", onKeyDown);
    return () => {
      root.removeEventListener("focusin", onFocusIn);
      root.removeEventListener("focusout", onFocusOut);
      root.removeEventListener("keydown", onKeyDown);
      clearActiveFieldEsc();
    };
  }, [open, containerRef]);

  useEscLayer(open, () => {
    const root = containerRef.current;
    if (isFieldFocusedInRoot(root)) return;
    if (onTabBackRef.current?.()) return;
    onCloseRef.current?.();
  });
}
