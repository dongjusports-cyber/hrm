import { useLocation } from "react-router-dom";
import { useAuth } from "./authStore";
import { useFullscreen } from "./useFullscreen";

/**
 * Nút thử nghiệm — toàn màn hình trình duyệt (ẩn thanh Chrome).
 * Chỉ hiện Portal staff; Worker app dùng PWA cài riêng.
 */
export function FullscreenToggle() {
  const { accessToken } = useAuth();
  const location = useLocation();
  const { active, supported, toggle } = useFullscreen();

  const onWorker = location.pathname.startsWith("/worker");
  const onLogin =
    location.pathname === "/login" ||
    location.pathname === "/worker/login" ||
    location.pathname === "/change-password";

  if (!accessToken || onWorker || onLogin || !supported) return null;

  return (
    <button
      type="button"
      className={`fullscreen-toggle-btn${active ? " is-active" : ""}`}
      onClick={() => void toggle()}
      title={
        active
          ? "Thoát toàn màn hình (Esc hoặc F11)"
          : "Toàn màn hình — ẩn thanh Chrome (thử nghiệm)"
      }
      aria-pressed={active}
      aria-label={active ? "Thoát toàn màn hình" : "Bật toàn màn hình"}
    >
      <span className="fullscreen-toggle-icon" aria-hidden>
        {active ? "⤢" : "⛶"}
      </span>
      <span className="fullscreen-toggle-label">{active ? "Thoát" : "Toàn màn"}</span>
    </button>
  );
}
