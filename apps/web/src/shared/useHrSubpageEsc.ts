import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { navigateSmooth } from "./navigateSmooth";
import { useEscLayer } from "./useEscLayer";

/**
 * @locked ESC trang con HR — xem `.cursor/rules/esc-keyboard.mdc`
 */
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
