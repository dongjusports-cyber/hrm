import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "./authStore";

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** Phím tắt toàn cục (không hiển thị thanh — xem HIEN_PHAP/PHIM_TAT_HR.md). */
export function KeyboardHintsBar() {
  const { accessToken } = useAuth();
  const location = useLocation();

  const onWorker = location.pathname.startsWith("/worker");
  const onLogin =
    location.pathname === "/login" ||
    location.pathname === "/worker/login" ||
    location.pathname === "/change-password";

  useEffect(() => {
    if (!accessToken || onWorker || onLogin) return;

    function onKey(e: KeyboardEvent) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;
      e.preventDefault();
      const el = document.querySelector<HTMLElement>(
        "[data-hotkey-search], .hr-toolbar-search, .tk-search input, input[placeholder*='MSNV']",
      );
      el?.focus();
      (el as HTMLInputElement | null)?.select?.();
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [accessToken, onWorker, onLogin]);

  return null;
}
