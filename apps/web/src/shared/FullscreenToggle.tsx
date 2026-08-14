import { useLocation } from "react-router-dom";
import { useAuth } from "./authStore";
import { useFullscreen } from "./useFullscreen";

/**
 * Nút Full — phóng to trình duyệt. Chỉ «Thoát» mới thoát; ESC = quay tab.
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
          ? "Thoát phóng to — chỉ bấm chuột (Esc: quay tab / hoàn tác ô nhập)"
          : "Full — phóng to toàn màn hình (chỉ bấm chuột để thoát)"
      }
      aria-pressed={active}
      aria-label={active ? "Thoát phóng to" : "Phóng to toàn màn hình"}
    >
      <span className="fullscreen-toggle-icon" aria-hidden>
        {active ? "⤢" : "⛶"}
      </span>
      <span className="fullscreen-toggle-label">{active ? "Thoát" : "Full"}</span>
    </button>
  );
}
