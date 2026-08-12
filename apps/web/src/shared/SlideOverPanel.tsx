import { ReactNode } from "react";
import { useEscLayer } from "./useEscLayer";

type Props = {
  open: boolean;
  title?: string;
  onClose: () => void;
  children?: ReactNode;
};

/**
 * Khay trượt phải (HUD) — mở/đóng bằng CSS transform, không animation liên tục.
 * Dùng cho xem chi tiết NV / tìm kiếm sau này.
 */
export function SlideOverPanel({
  open,
  title = "Chi tiết",
  onClose,
  children,
}: Props) {
  useEscLayer(open, onClose);

  return (
    <>
      <button
        type="button"
        className={`slide-over-overlay${open ? " is-open" : ""}`}
        aria-label="Đóng khay chi tiết"
        tabIndex={open ? 0 : -1}
        onClick={onClose}
      />
      <aside
        className={`slide-over-panel${open ? " is-open" : ""}`}
        aria-hidden={!open}
        aria-label={title}
      >
        <header className="slide-over-head">
          <h3>{title}</h3>
          <button
            type="button"
            className="slide-over-close"
            onClick={onClose}
            aria-label="Đóng"
          >
            ×
          </button>
        </header>
        <div className="slide-over-body">{children}</div>
      </aside>
    </>
  );
}
