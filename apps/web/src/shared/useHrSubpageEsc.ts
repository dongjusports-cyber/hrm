import { useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useEscLayer } from "./useEscLayer";

/**
 * @locked ESC trang con HR — xem `.cursor/rules/esc-keyboard.mdc`
 *
 * Dùng `navigate` thẳng (không View Transition). startViewTransition đang chạy
 * hoặc throw → ESC không đi đâu, kẹt trang.
 */
export function useHrSubpageEsc(options?: {
  onDismiss?: () => boolean;
  backTo?: string;
}) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const backTo = options?.backTo ?? "/m/hr";
  const dismissRef = useRef(options?.onDismiss);
  dismissRef.current = options?.onDismiss;

  useEscLayer(true, () => {
    if (dismissRef.current?.()) return;
    if (pathname === backTo || pathname === `${backTo}/`) return false;
    navigate(backTo);
  });
}
