import { ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";

type Props = {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  /** Nút hành động chính (vd. Lưu) — hiển thị cạnh nút đóng. */
  actions?: ReactNode;
  /** Chỉ vùng con cuộn; header/tab cố định (hồ sơ NV). */
  inFrameScroll?: boolean;
  /** Ẩn thanh tiêu đề — chrome nằm trong children (hồ sơ NV). */
  hideHeader?: boolean;
};

/** Cửa sổ nổi full màn hình — form tập trung, danh sách phía sau vẫn giữ ngữ cảnh. */
export function FullScreenSheet({
  open,
  title,
  subtitle,
  onClose,
  children,
  actions,
  inFrameScroll = false,
  hideHeader = false,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fs-sheet-backdrop" role="presentation" onClick={onClose}>
      <div
        className={hideHeader ? "fs-sheet fs-sheet--no-head" : "fs-sheet"}
        role="dialog"
        aria-modal="true"
        aria-label={hideHeader ? title : undefined}
        aria-labelledby={hideHeader ? undefined : "fs-sheet-title"}
        onClick={(e) => e.stopPropagation()}
      >
        {!hideHeader && (
          <header className="fs-sheet-head">
            <div className="fs-sheet-head-text">
              <h2 id="fs-sheet-title">{title}</h2>
              {subtitle && <p className="field-hint fs-sheet-subtitle">{subtitle}</p>}
            </div>
            <div className="fs-sheet-head-actions">
              {actions}
              <button type="button" className="btn-ghost-dark fs-sheet-close" onClick={onClose}>
                × Đóng
              </button>
            </div>
          </header>
        )}
        <div
          className={inFrameScroll ? "fs-sheet-body fs-sheet-body-shell" : "fs-sheet-body"}
        >
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}
