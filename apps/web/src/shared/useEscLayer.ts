import { useEffect, useRef } from "react";
import { registerEscHandler, type EscHandler } from "./escStack";

/**
 * @locked Đăng ký tầng ESC — dùng escStack, không tự addEventListener Escape.
 * Xem `.cursor/rules/esc-keyboard.mdc`
 *
 * `onEsc` trả `false` nếu không xử lý — tầng dưới / quay trang vẫn chạy.
 * Không được `return` im lặng khi chưa đóng overlay / chưa quay trang.
 */
export function useEscLayer(active: boolean, onEsc: EscHandler) {
  const ref = useRef(onEsc);
  ref.current = onEsc;

  useEffect(() => {
    if (!active) return;
    return registerEscHandler(() => ref.current());
  }, [active]);
}
