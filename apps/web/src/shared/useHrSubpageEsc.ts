import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { navigateSmooth } from "./navigateSmooth";
import { useEscLayer } from "./useEscLayer";

/** ESC trên màn con HR: đóng overlay/tab con trước, sau đó về `backTo` (mặc định hub `/m/hr`). */
export function useHrSubpageEsc(options?: {
  onDismiss?: () => boolean;
  backTo?: string;
}) {
  const navigate = useNavigate();
  const backTo = options?.backTo ?? "/m/hr";
  const dismissRef = useRef(options?.onDismiss);
  dismissRef.current = options?.onDismiss;

  useEscLayer(true, () => {
    if (dismissRef.current?.()) return;
    navigateSmooth(navigate, backTo);
  });
}
