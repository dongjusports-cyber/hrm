import { useEffect, useRef } from "react";
import { registerEscHandler } from "./escStack";

/**
 * @locked Đăng ký tầng ESC — dùng escStack, không tự addEventListener Escape.
 * Xem `.cursor/rules/esc-keyboard.mdc`
 */
export function useEscLayer(active: boolean, onEsc: () => void) {
  const ref = useRef(onEsc);
  ref.current = onEsc;

  useEffect(() => {
    if (!active) return;
    return registerEscHandler(() => ref.current());
  }, [active]);
}
