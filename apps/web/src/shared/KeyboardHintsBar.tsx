import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "./authStore";

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** Thanh phím tắt §23.2 — góc dưới trái, không che FAB AI. */
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
      el?.select?.();
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [accessToken, onWorker, onLogin]);

  if (!accessToken || onWorker || onLogin) return null;

  return (
    <footer className="kbd-hints-bar" aria-label="Phím tắt">
      <span>
        <kbd>/</kbd> Tìm
      </span>
      <span>
        <kbd>Ctrl+K</kbd> Lệnh
      </span>
      <span>
        <kbd>Esc</kbd> Đóng
      </span>
      <span className="kbd-hints-muted">
        <kbd>F2</kbd> Sửa ô (lưới)
      </span>
    </footer>
  );
}
