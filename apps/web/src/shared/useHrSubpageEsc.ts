import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { navigateSmooth } from "./navigateSmooth";

/** ESC trên màn con HR: đóng overlay/form trước, sau đó về `backTo` (mặc định hub `/m/hr`). */
export function useHrSubpageEsc(options?: {
  onDismiss?: () => boolean;
  backTo?: string;
}) {
  const navigate = useNavigate();
  const backTo = options?.backTo ?? "/m/hr";
  const dismissRef = useRef(options?.onDismiss);
  dismissRef.current = options?.onDismiss;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (dismissRef.current?.()) {
        e.preventDefault();
        e.stopImmediatePropagation();
        return;
      }
      e.preventDefault();
      e.stopImmediatePropagation();
      navigateSmooth(navigate, backTo);
    }
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [navigate, backTo]);
}
