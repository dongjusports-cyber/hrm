import { type RefObject, useEffect, useRef, useState } from "react";
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

type SheetKeyboardOptions = {
  open: boolean;
  containerRef: RefObject<HTMLElement | null>;
  /** ESC khi không đang sửa ô — quay tab trước. Trả true nếu đã xử lý. */
  onTabBack?: () => boolean;
  /** ESC khi `onTabBack` không xử lý — đóng sheet / quay trang trước (≈ nút Đóng). */
  onClose?: () => void;
};

/**
 * ESC trong ô nhập: hoàn tác về giá trị lúc focus, blur khỏi ô.
 * Enter trong ô (trừ textarea): blur = commit qua onBlur/onChange.
 * ESC ngoài ô: `onTabBack` trước, rồi `onClose`.
 */
export function useSheetKeyboard({ open, containerRef, onTabBack, onClose }: SheetKeyboardOptions) {
  const [fieldEditing, setFieldEditing] = useState(false);
  const snapshotRef = useRef<{
    el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
    value: string;
  } | null>(null);
  const onTabBackRef = useRef(onTabBack);
  onTabBackRef.current = onTabBack;
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) {
      setFieldEditing(false);
      snapshotRef.current = null;
      return;
    }
    const root = containerRef.current;
    if (!root) return;

    function onFocusIn(e: FocusEvent) {
      if (!isEditableFormField(e.target)) {
        setFieldEditing(false);
        snapshotRef.current = null;
        return;
      }
      snapshotRef.current = { el: e.target, value: getFieldValue(e.target) };
      setFieldEditing(true);
    }

    function onFocusOut(e: FocusEvent) {
      const related = e.relatedTarget as Node | null;
      if (root && related && root.contains(related) && isEditableFormField(related)) return;
      setFieldEditing(false);
      snapshotRef.current = null;
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
    };
  }, [open, containerRef]);

  useEscLayer(open && fieldEditing, () => {
    const snap = snapshotRef.current;
    if (!snap) return;
    setFormFieldValue(snap.el, snap.value);
    snap.el.blur();
    setFieldEditing(false);
    snapshotRef.current = null;
  });

  useEscLayer(open && !fieldEditing, () => {
    if (onTabBackRef.current?.()) return;
    onCloseRef.current?.();
  });
}
