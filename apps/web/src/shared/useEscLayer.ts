import { useEffect, useRef } from "react";
import { registerEscHandler } from "./escStack";

/** Đăng ký một tầng ESC — chỉ active khi `active === true`. */
export function useEscLayer(active: boolean, onEsc: () => void) {
  const ref = useRef(onEsc);
  ref.current = onEsc;

  useEffect(() => {
    if (!active) return;
    return registerEscHandler(() => ref.current());
  }, [active]);
}
